from datetime import date
from math import ceil
from ortools.sat.python import cp_model
from collections import defaultdict
from .models import TimeSlot, Space, Schedule, Module, Group
from users.models import AdvancedUserProfile, BasicUserProfile
from django.db import transaction
from django.db.models import Count
from users.models import busyTimeSelect


def generate_schedule_for_specialities(specialities, semester=None):
    try:
        specialities_departments = [spc.level.departement for spc in specialities]

        # TIME
        time_days = TimeSlot.objects.filter(departements__in=specialities_departments).distinct()
        days = time_days.values_list('day__name', flat=True).distinct()
        timeslots = {}
        for day in days:
            timeslots[day] = [time.start_time.strftime("%H:%M") for time in time_days]

        # CLASSROOMS
        Spaces = Space.objects.filter(departements__in=specialities_departments)
        spaces = {}
        for each in Spaces:
            if each.room_type.name not in spaces:
                spaces[each.room_type.name] = []
            spaces[each.room_type.name].append((each, each.capacity//2))





        # Extract enseignants that are already exists in db timetables and teach in this department
        existing_prof_time_slots = set(
            Schedule.objects.filter(speciality__in=specialities, is_activated=True).values_list(
                'professor', 'day', 'time'))


        # Calculate academic year
        today = date.today()
        year = today.year
        month = today.month

        if 6 <= month <= 12:
            academic_year = f"{year}/{year + 1}"
        else:
            academic_year = f"{year - 1}/{year}"
        print(f"\n📚 Using Academic Year: {academic_year}")


        pending_saves = []


        for speciality in specialities:
            print("\n-----------------------\n", speciality, " : ")

            model = cp_model.CpModel()
            cours_tous_assignments = {}
            time_penalties = {}

            # Fetch modules
            if semester == "S1":
                modules = Module.objects.filter(specialityMod=speciality, semester='s1', mode_evaluation="Both" or "Examen", is_activated=True)
            elif semester == "S2":
                modules = Module.objects.filter(specialityMod=speciality, semester='s2', mode_evaluation="Both" or "Examen", is_activated=True)
            else:
                modules = Module.objects.filter(specialityMod=speciality, mode_evaluation="Both" or "Examen",is_activated=True)

            module_lookup = {m.module_name: m for m in modules}
            module_professors=[]

            for module in modules:
                professors = AdvancedUserProfile.objects.filter(modules=module)
                if professors.exists():
                    for p in professors:
                        if p not in module_professors:
                            module_professors.append(p)


            # GROUPS
            Groups = Group.objects.filter(speciality__in=speciality)
            groups = []
            group_studentNum={}
            for group in Groups:
                groups.append(group.group_number)
                students = BasicUserProfile.objects.filter(speciality=speciality, group=group)
                group_studentNum[group]=students.count()


            # groupping groups in salles based on capacity--------------------------------------------------
            specDivisionGroups = {}
            for room in spaces.values():
                specDivisionGroups[room[0]] = []
                cap = 0
                examGroups = []
                for i, group1 in enumerate(groups):
                    for group in groups[i:]:
                        groupStudents = group_studentNum[group]
                        if room[1] >= groupStudents:
                            cap += groupStudents
                            if cap > room[1]:
                                cap -= groupStudents
                                continue
                            elif cap <= room[1]:
                                if group not in examGroups:
                                    examGroups.append(group)
                if len(examGroups) != 0:
                    specDivisionGroups[room[0]].append(examGroups)


            # Create assignments
            for prof in module_professors:
                for module in modules:
                    for room, specDivisionGroup in specDivisionGroups.items():
                        for group in specDivisionGroup:
                            for day_idx, day in enumerate(days):
                                for hour_idx, hour in enumerate(timeslots[day]):
                                    key = (speciality, group, module, prof, room, day, hour)
                                    cours_tous_assignments[key] = model.NewBoolVar(f"exam_{key}")

                                    hour_value = int(hour.split(':')[0])
                                    time_penalty = hour_value
                                    time_penalties[key] = time_penalty






            print("length of Assignements : ", len(cours_tous_assignments))

            '''# Constraints
            # 1. One session per module
            module_vars = defaultdict(list)
            for key, var in cours_tous_assignments.items():
                module_vars[key[2]].append(var)
            for key, vars in module_vars.items():
                currentModule = module_lookup.get(key)
                if not currentModule:
                    continue
                required_hours = currentModule.examTimeslots
                model.Add(sum(vars) == required_hours)

            # 2. No professor double booking
            prof_times = defaultdict(list)
            for key, var in cours_tous_assignments.items():
                prof_times[(key[4], key[7], key[8])].append(var)
            for vars in prof_times.values():
                model.Add(sum(vars) <= 1)

            # respect prof indisponibités
            indispos = busyTimeSelect.objects.filter(user__modules__specialityMod=speciality, is_approved=True)
            prof_busy_times = set()
            for entry in indispos:
                prof = AdvancedUserProfile.objects.get(first_name=entry.user.first_name,
                                                       last_name=entry.user.last_name)

                day = entry.busyday.name
                for time in entry.busytime.all():
                    time_str = time.start_time.strftime("%H:%M")
                    prof_busy_times.add((prof, day, time_str))

            for key, var in cours_tous_assignments.items():
                prof = key[4]
                day = key[7]
                hour = key[8]
                if (prof, day, hour) in prof_busy_times:
                    model.Add(var == 0)

            # 3. No room double booking
            room_times = defaultdict(list)
            for key, var in cours_tous_assignments.items():
                if key[5] != "Enligne" and key[6] != "Enligne":
                    room_times[(key[5], key[6], key[7], key[8])].append(var)
            for vars in room_times.values():
                model.Add(sum(vars) <= 1)

            # 4. Avoid conflicts with pending_saves
            for key, var in cours_tous_assignments.items():
                for scheduled in pending_saves:
                    if (scheduled['room_type'] == key[5] and
                            scheduled['room_number'] == key[6] and
                            scheduled['day'] == key[7] and
                            scheduled['time'] == key[8]):
                        model.Add(var == 0)
                    if (scheduled['professor_name'] == key[4] and
                            scheduled['day'] == key[7] and
                            scheduled['time'] == key[8]):
                        model.Add(var == 0)



            # 5. avoid conflicts with departments shared rooms existing schedules
            shared_spaces = Space.objects.annotate(num_depts=Count('departements')).filter(num_depts__gt=1).distinct()
            # Get schedules in those shared rooms made by other departments
            busy_shared_slots = Schedule.objects.filter(
                room_number__in=[shared_space.room_number for shared_space in shared_spaces],
                room_type__in=[shared_space.room_type.name for shared_space in shared_spaces],
                is_activated=True).exclude(speciality__in=specialities).values('room_number', 'room_type', 'day', 'time')

            # Convert to a set for fast lookup
            busy_shared_set = {(b['room_type'], b['room_number'], b['day'], b['time']) for b in busy_shared_slots}

            for key, var in cours_tous_assignments.items():
                # Avoid shared room if busy elsewhere
                if (key[5], key[6], key[7], key[8]) in busy_shared_set:
                    if key[5] != "Enligne" and key[6] != "Enligne":
                        model.Add(var == 0)


            # 6. avoid conflicts with specialities shared rooms existing schedules

            # Get schedules in those shared rooms by other specialities
            busy_shared_slots = Schedule.objects.filter(
                room_number__in=[space.room_number for space in Spaces],
                room_type__in=[space.room_type.name for space in Spaces],
                is_activated=True).exclude(speciality__in=specialities).values('room_number','room_type', 'day','time')
            # Convert to a set for fast lookup
            busy_shared_set = {(b['room_type'], b['room_number'], b['day'], b['time']) for b in busy_shared_slots}

            for key, var in cours_tous_assignments.items():
                # Avoid shared room if busy elsewhere
                if (key[5], key[6], key[7], key[8]) in busy_shared_set:
                    if key[5] != "Enligne" and key[6] != "Enligne":
                        model.Add(var == 0)


            # 6. No Tous grp double booking
            group_times = defaultdict(list)
            for key, var in cours_tous_assignments.items():
                group_times[(key[0], key[1], key[7], key[8])].append(var)
            for vars in group_times.values():
                model.Add(sum(vars) <= 1)


            # 8. Avoid professor time conflicts with existing schedules
            for key, var in cours_tous_assignments.items():
                if (key[4], key[7], key[8]) in existing_prof_time_slots:
                    model.Add(var == 0)

            # Soft-Constraint time : Cours should be before 12hAM
            # NEW: Optimize for earlier times
            # Create a weighted sum where earlier times are preferred
            time_preference_terms = []
            for key, var in cours_tous_assignments.items():
                time_preference_terms.append(
                    var * (100 - time_penalties[key]))  # Higher score for earlier times

            # Solve with two objectives:
            # 1. First priority: schedule all Cours sessions
            # 2. Second priority: prefer earlier times

            # Solve Cours-Tous only
            model.Maximize(
                sum(cours_tous_assignments.values()) * 1000 +  # Primary objective (ensure all scheduled)
                sum(time_preference_terms))  # Secondary objective (time preference)

            solver = cp_model.CpSolver()
            solver.parameters.num_search_workers = 8
            status = solver.Solve(model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                for key, var in cours_tous_assignments.items():
                    if solver.Value(var) == 1:
                        pending_saves.append({
                            'speciality': key[0],
                            'group': key[1],
                            'module_name': key[2],
                            'typeModule': key[3],
                            'professor_name': key[4],
                            'room_type': key[5],
                            'room_number': key[6],
                            'day': key[7],
                            'time': key[8],
                            'school_year': academic_year
                        })
            else:
                print(f"❌ No feasible solution for Cours-Tous in {speciality.name}")


        with transaction.atomic():
            Schedule.objects.filter(speciality__in=specialities, is_activated=True).delete()

            for entry in pending_saves:
                try:
                    module = Module.objects.get(specialityMod=entry['speciality'], module_name=entry['module_name'],
                                                is_activated=True)

                    Schedule.objects.create(
                        speciality=entry['speciality'],
                        group=entry['group'],
                        module=module,
                        typeModule=entry['typeModule'],
                        section=entry['section'],
                        professor=entry['professor_name'],
                        room_type=entry['room_type'],
                        room_number=entry['room_number'],
                        day=entry['day'],
                        time=entry['time'],
                        school_year=entry['school_year']
                    )
                except Exception as e:
                    print(f"Error saving schedule: {e}")'''

    except Exception as e:
        print(f"Error during generation: {e}")
