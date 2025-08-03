from datetime import date
from math import ceil
from ortools.sat.python import cp_model
from collections import defaultdict
from .models import TimeSlot, Space, Schedule, Speciality, Module, Group
from users.models import AdvancedUserProfile
from django.db import transaction
from django.db.models import Count
from users.models import busyTimeSelect


def generate_schedule_for_specialities(specialities, semester=None):
    try:
        specialities_departments = [spc.level.departement for spc in specialities]

        # TIME
        time_days = TimeSlot.objects.filter(departements__in=specialities_departments).distinct()
        days = time_days.values_list('day__name', flat=True).distinct()

        day_order = {
            'DIMANCHE': 0,
            'LUNDI': 1,
            'MARDI': 2,
            'MERCREDI': 3,
            'JEUDI': 4,
            'SAMEDI': 5
        }

        days = sorted(days, key=lambda day: day_order.get(day, 99))

        print(days)
        timeslots = {}
        for day in days:
            timeslots[day] = [time.start_time.strftime("%H:%M") for time in time_days]

        print(timeslots)

        # CLASSROOMS
        Spaces = Space.objects.filter(departements__in=specialities_departments)
        spaces = {}
        for each in Spaces:
            if each.room_type.name not in spaces:
                spaces[each.room_type.name] = []
            spaces[each.room_type.name].append(each.room_number)
        spaces["Enligne"] = []
        spaces["Enligne"].append("Enligne")

        # GROUPS
        groups = defaultdict(dict)
        Groups = Group.objects.filter(speciality__in=specialities)

        temp_groups_by_speciality = defaultdict(list)
        for group in Groups:
            temp_groups_by_speciality[group.speciality].append(group)


        for speciality, groupslist in temp_groups_by_speciality.items():
            if all(group.section not in [0, None] for group in groupslist):
                for group in groupslist:
                    section_name = f"Section{group.section}"
                    if section_name not in groups[speciality]:
                        groups[speciality][section_name] = []
                    groups[speciality][section_name].append(group.group_number)
                print(groups)

            else:
                sections = speciality.sections or 1
                groups_per_section = ceil(len(groupslist) / sections)
                for i in range(sections):
                    start = i * groups_per_section
                    end = start + groups_per_section
                    section_name = f"Section{i + 1}"
                    groups[speciality][section_name] = groupslist[start:end]

                    for group in groupslist[start:end]:
                        try:
                            group_obj = Group.objects.get(group_number=group.group_number, speciality=speciality)
                            group_obj.section = i + 1
                            group_obj.save()
                        except Group.DoesNotExist:
                            print(f"⚠️ Groupe {group.group_number} not found in DB — check data!")

                print(group for group in groups)
                # Add "Tous" if applicable
        for speciality, sections in groups.items():
            for section_name, group_list in sections.items():
                if (
                        speciality.level.departement.est.SystemeEtudeEnGroupe == "Groupes-Tous"
                        and len(group_list) >= 2
                        and "Tous" not in group_list  # avoid duplicates!
                ):
                    group_list.append("Tous")


        # Calculate academic year
        today = date.today()
        year = today.year
        month = today.month

        if 6 <= month <= 12:
            academic_year = f"{year}/{year + 1}"
            start_date = date(year, 6, 15)
            end_date = date(year+1 , 12, 15)
        else:
            academic_year = f"{year - 1}/{year}"
            start_date = date(year-1, 6, 15)
            end_date = date(year, 12, 15)
        print(f"\n📚 Using Academic Year: {academic_year}")

        # Extract enseignants that are already exists in db timetables and teach in this department
        if semester in ["s1", "s2"]:
            existing_prof_time_slots = set(
                Schedule.objects.filter(speciality__in=specialities, school_year=academic_year,semester=semester,
                                        is_activated=True).values_list('professor', 'day', 'time'))
        else:
            existing_prof_time_slots = set(
                Schedule.objects.filter(speciality__in=specialities,school_year=academic_year,
                                        is_activated=True).values_list('professor', 'day', 'time'))

        pending_saves = []

        for speciality in specialities:
            sections = groups.get(speciality, {}).keys()
            for section_name in sections:
                current_groups = groups[speciality].get(section_name, [])
                has_tous = "Tous" in current_groups
                print("\n-----------------------\n", speciality, " : ", section_name)

                # PHASE 1: Schedule Cours for Tous groups if they exist
                if has_tous:
                    model = cp_model.CpModel()
                    cours_tous_assignments = {}
                    time_penalties = {}

                    # Fetch modules
                    if semester in ["s1","s2"]:
                        modules = Module.objects.filter(specialityMod=speciality, semester=semester, is_activated=True)
                    else:
                        modules = Module.objects.filter(specialityMod=speciality, is_activated=True)

                    module_lookup = {m.module_name: m for m in modules}
                    module_professors_dict = {}

                    for module in modules:
                        if not module.Cours and module.nbrCoursSemaine in [None, 0]:
                            continue
                        professors = AdvancedUserProfile.objects.filter(modules=module)
                        if professors.exists():
                            module_professors_dict[module.module_name] = [p for p in professors]

                    # Create assignments only for Cours-Tous
                    for module, prof_list in module_professors_dict.items():
                        if module_lookup[module].Cours is None:
                            rtype = "Enligne"
                        else:
                            rtype = module_lookup[module].Cours.name
                            if rtype not in spaces:
                                continue

                        for prof in prof_list:
                            enseignant = AdvancedUserProfile.objects.get(id=prof.id)
                            if enseignant.grade and not enseignant.grade.teachCours:
                                continue
                            for room in spaces[rtype]:
                                for day_idx, day in enumerate(days):
                                    for hour_idx, hour in enumerate(timeslots[day]):
                                        key = (speciality, "Tous", module, "Cours", prof, rtype, room, day, hour)
                                        cours_tous_assignments[key] = model.NewBoolVar(f"cours_tous_{key}")
                                        # Create a penalty score based on time (earlier = better)
                                        # Morning sessions (before 12:00) get lower penalty
                                        hour_value = int(hour.split(':')[0])
                                        if 8 < hour_value <= 12 and rtype != "Enligne":  # Morning
                                            time_penalty = 0 + day_idx  # Earlier hours have lower penalty
                                        elif hour_value in [8] and rtype != "Enligne":
                                            time_penalty = 5 + day_idx
                                        elif hour_value > 14 and rtype == "Enligne":
                                            time_penalty = 0 + day_idx
                                        else:  # Afternoon
                                            time_penalty = 15 + day_idx  # Afternoon gets higher penalty

                                        time_penalties[key] = time_penalty
                    print("length of Cours Tous Assignements : ", len(cours_tous_assignments))

                    # Constraints for Cours-Tous only
                    # 1. One session per module
                    module_vars = defaultdict(list)
                    for key, var in cours_tous_assignments.items():
                        module_vars[key[2]].append(var)
                    for key, vars in module_vars.items():
                        currentModule = module_lookup.get(key)
                        if not currentModule:
                            continue
                        required_hours = currentModule.nbrCoursSemaine or 1
                        model.Add(sum(vars) == required_hours)

                    # 2. No professor double booking
                    prof_times = defaultdict(list)
                    for key, var in cours_tous_assignments.items():
                        prof_times[(key[4], key[7], key[8])].append(var)
                    for vars in prof_times.values():
                        model.Add(sum(vars) <= 1)

                    # respect prof indisponibités
                    indispos = busyTimeSelect.objects.filter(user__modules__specialityMod=speciality, is_approved=True,
                                                             timestamp__date__range=(start_date, end_date))
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

                            if (scheduled['speciality'] == key[0] and
                                    scheduled['room_type'] == "Enligne" and
                                    scheduled['room_number'] == "Enligne" and
                                    scheduled['day'] == key[7] and
                                    scheduled['time'] == key[8] and
                                    scheduled['section'] != section_name): continue

                            if (scheduled['speciality'] != key[0] and
                                    scheduled['room_type'] == "Enligne" and
                                    scheduled['room_number'] == "Enligne" and
                                    scheduled['day'] == key[7] and
                                    scheduled['time'] == key[8]): continue

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
                        is_activated=True,school_year=academic_year,semester=semester).exclude(speciality__in=specialities).values('room_number', 'room_type', 'day', 'time')

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
                        is_activated=True,school_year=academic_year,semester=semester).exclude(speciality__in=specialities).values('room_number','room_type', 'day','time')
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

                    '''# Calculate target Cours per day
                    total_cours = len(module_professors_dict)
                    num_days = len(days)
                    #target_min = total_cours // num_days
                    target_max = ceil(total_cours / (num_days-2))+1
                    print(target_max)

                    # Track Cours per day
                    cours_per_day = {day: [] for day in days}
                    for key, var in cours_tous_assignments.items():
                        day = key[7]
                        cours_per_day[day].append(var)

                    # 7 : Balance Cours across days
                    for day, vars in cours_per_day.items():
                        # At least target_min Cours per day
                        if target_min > 0:
                            model.Add(sum(vars) >= target_min)
                        # At most target_max Cours per day
                        model.Add(sum(vars) <= target_max)'''

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
                                    'section': section_name,
                                    'professor_name': key[4],
                                    'room_type': key[5],
                                    'room_number': key[6],
                                    'day': key[7],
                                    'time': key[8],
                                    'school_year': academic_year
                                })
                    else:
                        print(f"❌ No feasible solution for Cours-Tous in {speciality.name} {section_name}")

                # PHASE 2: Schedule all other sessions (TD, TP, and Cours for non-Tous groups)
                model = cp_model.CpModel()
                other_assignments = {}
                other_time_penalties = {}

                # Fetch modules
                if semester in ["s1","s2"]:
                    modules = Module.objects.filter(specialityMod=speciality, semester=semester, is_activated=True)
                else:
                    modules = Module.objects.filter(specialityMod=speciality, is_activated=True)

                module_lookup = {m.module_name: m for m in modules}
                module_content = {}
                module_professors_dict = {}

                for module in modules:
                    content = {}
                    if module.TD:
                        content["TD"] = module.TD.name
                    elif not module.TD and module.nbrTDSemaine not in [None, 0]:
                        content["TD"] = "Enligne"

                    if module.TP:
                        content["TP"] = module.TP.name
                    elif not module.TP and module.nbrTPSemaine not in [None, 0]:
                        content["TP"] = "Enligne"

                    if module.Cours:
                        content["Cours"] = module.Cours.name
                    elif not module.Cours and module.nbrCoursSemaine not in [None, 0]:
                        content["Cours"] = "Enligne"

                    if content:
                        module_content[module.module_name] = content

                    professors = AdvancedUserProfile.objects.filter(modules=module)
                    if professors.exists():
                        module_professors_dict[module.module_name] = [p for p in professors]

                # Create assignments for non-Tous groups and non-Cours types
                for module, prof_list in module_professors_dict.items():
                    for group in current_groups:
                        if group == "Tous":
                            continue  # Skip Tous group (already handled)

                        for prof in prof_list:
                            enseignant = AdvancedUserProfile.objects.get(id=prof.id)
                            for mtype, rtype in module_content.get(module, {}).items():
                                if mtype == "Cours" and group != "Tous" and has_tous:
                                    continue  # Skip Cours for non-Tous groups if needed
                                if rtype not in spaces:
                                    continue
                                if mtype == "Cours" and enseignant.grade and not enseignant.grade.teachCours:
                                    continue

                                if mtype == "TD" and enseignant.grade and not enseignant.grade.teachTD:
                                    continue

                                if mtype == "TP" and enseignant.grade and not enseignant.grade.teachTP:
                                    continue

                                for room in spaces[rtype]:
                                    for day_idx, day in enumerate(days):
                                        for hour_idx, hour in enumerate(timeslots[day]):
                                            key = (speciality, group, module, mtype, prof, rtype, room, day, hour)
                                            other_assignments[key] = model.NewBoolVar(f"other_{key}")
                                            hour_value = int(hour.split(':')[0])

                                            if mtype == "TD" or mtype == "TP":
                                                # Prefer late morning for TD
                                                if 8 <= hour_value <= 14 and rtype != "Enligne":
                                                    penalty = 0 + day_idx
                                                elif hour_value > 14 and rtype == "Enligne":
                                                    penalty = 0 + day_idx
                                                else:
                                                    penalty = 10 + day_idx  # Avoid afternoon

                                            else:  # Non-Tous Cours
                                                # Same preference as Tous Cours
                                                if 8 <= hour_value <= 12 and rtype != "Enligne":
                                                    penalty = 0 + day_idx
                                                elif hour_value > 12 and rtype != "Enligne":
                                                    penalty = 5 + day_idx
                                                elif hour_value > 14 and rtype == "Enligne":
                                                    penalty = 0 + day_idx
                                                else:
                                                    penalty = 10 + day_idx

                                            other_time_penalties[key] = penalty

                print("length of Other Assignements : ", len(other_assignments))
                # Constraints for other sessions

                # 1. Required hours per module type
                group_module_vars = defaultdict(list)
                for key, var in other_assignments.items():
                    group_module_vars[(key[1], key[2], key[3])].append(var)
                for (group, module, mtype), vars in group_module_vars.items():
                    required_hours = 0

                    currentModule = module_lookup.get(module)
                    if not currentModule:
                        continue

                    if mtype == "TD":
                        required_hours = currentModule.nbrTDSemaine or 1
                    if mtype == "TP":
                        required_hours = currentModule.nbrTPSemaine or 1
                    if mtype == "Cours":
                        required_hours = currentModule.nbrCoursSemaine or 1
                    if required_hours > 0:
                        model.Add(sum(vars) == required_hours)

                # 2. No professor double booking
                prof_times = defaultdict(list)
                for key, var in other_assignments.items():
                    prof_times[(key[4], key[7], key[8])].append(var)
                for vars in prof_times.values():
                    model.Add(sum(vars) <= 1)

                # respect prof indisponibités

                indispos = busyTimeSelect.objects.filter(user__modules__specialityMod=speciality, is_approved=True,
                                                         timestamp__date__range=(start_date, end_date))
                prof_busy_times = set()
                for entry in indispos:
                    prof = AdvancedUserProfile.objects.get(first_name=entry.user.first_name,
                                                           last_name=entry.user.last_name)
                    day = entry.busyday.name
                    for time in entry.busytime.all():
                        time_str = time.start_time.strftime("%H:%M")
                        prof_busy_times.add((prof, day, time_str))

                for key, var in other_assignments.items():
                    prof = key[4]
                    day = key[7]
                    hour = key[8]
                    if (prof, day, hour) in prof_busy_times:
                        model.Add(var == 0)

                # 4. No room double booking
                room_times = defaultdict(list)
                for key, var in other_assignments.items():
                    if key[5] != "Enligne" and key[6] != "Enligne":
                        room_times[(key[5], key[6], key[7], key[8])].append(var)
                for vars in room_times.values():
                    model.Add(sum(vars) <= 1)

                # 5. No group double booking
                group_times = defaultdict(list)
                for key, var in other_assignments.items():
                    group_times[(key[0], key[1], key[7], key[8])].append(var)
                for vars in group_times.values():
                    model.Add(sum(vars) <= 1)

                # 6. Avoid conflicts with pending_saves (including Cours-Tous)
                for key, var in other_assignments.items():
                    for scheduled in pending_saves:
                        if (scheduled['speciality'] == key[0] and
                                scheduled['room_type'] == "Enligne" and
                                scheduled['room_number'] == "Enligne" and
                                scheduled['day'] == key[7] and
                                scheduled['time'] == key[8] and
                                scheduled['section'] != section_name): continue

                        if (scheduled['speciality'] != key[0] and
                                scheduled['room_type'] == "Enligne" and
                                scheduled['room_number'] == "Enligne" and
                                scheduled['day'] == key[7] and
                                scheduled['time'] == key[8]): continue

                        if (scheduled['room_type'] == key[5] and
                                scheduled['room_number'] == key[6] and
                                scheduled['day'] == key[7] and
                                scheduled['time'] == key[8]):
                            model.Add(var == 0)
                        if (scheduled['professor_name'] == key[4] and
                                scheduled['day'] == key[7] and
                                scheduled['time'] == key[8]):
                            model.Add(var == 0)

                        # Special conflict: No TD/TP when there's Cours-Tous for same speciality
                        if (scheduled['speciality'] == key[0] and
                                scheduled['section'] == section_name and
                                scheduled['group'] == "Tous" and
                                scheduled['typeModule'] == "Cours" and
                                scheduled['day'] == key[7] and
                                scheduled['time'] == key[8]):
                            model.Add(var == 0)

                # 7. avoid conflicts with departments shared rooms existing schedules
                shared_spaces = Space.objects.annotate(num_depts=Count('departements')).filter(num_depts__gt=1).distinct()
                # Get schedules in those shared rooms made by other departments
                busy_shared_slots = Schedule.objects.filter(
                    room_number__in=[shared_space.room_number for shared_space in shared_spaces],
                    room_type__in=[shared_space.room_type.name for shared_space in shared_spaces],
                    is_activated=True,school_year=academic_year,semester=semester).exclude(speciality__in=specialities).values('room_number','room_type','day','time')

                # Convert to a set for fast lookup
                busy_shared_set = {(b['room_type'], b['room_number'], b['day'], b['time']) for b in busy_shared_slots}

                for key, var in other_assignments.items():
                    # Avoid shared room if busy elsewhere
                    if (key[5], key[6], key[7], key[8]) in busy_shared_set:
                        if key[5]!="Enligne" and key[6]!="Enligne":
                            model.Add(var == 0)


                # 8. avoid conflicts with specialities shared rooms existing schedules

                # Get schedules in those shared rooms by other specialities
                busy_shared_slots = Schedule.objects.filter(
                    room_number__in=[space.room_number for space in Spaces],
                    room_type__in=[space.room_type.name for space in Spaces],
                    is_activated=True,school_year=academic_year,semester=semester).exclude(speciality__in=specialities).values('room_number', 'room_type',
                                                                                   'day', 'time')
                # Convert to a set for fast lookup
                busy_shared_set = {(b['room_type'], b['room_number'], b['day'], b['time']) for b in busy_shared_slots}

                for key, var in other_assignments.items():
                    # Avoid shared room if busy elsewhere
                    if (key[5], key[6], key[7], key[8]) in busy_shared_set:
                        if key[5]!="Enligne" and key[6]!="Enligne":
                            model.Add(var == 0)


                # 8. No Tous grp double booking
                group_times = defaultdict(list)
                for key, var in other_assignments.items():
                    group_times[(key[0], key[1], key[7], key[8])].append(var)
                for vars in group_times.values():
                    model.Add(sum(vars) <= 1)

                # 9. Avoid professor time conflicts with existing schedules
                for key, var in other_assignments.items():
                    if (key[4], key[7], key[8]) in existing_prof_time_slots:
                        model.Add(var == 0)

                # Soft-Constraint : 8<Cours<12  8<=TD,TP<=12
                time_preference_terms = []
                for key, var in other_assignments.items():
                    time_preference_terms.append(var * (100 - other_time_penalties[key]))

                # Solve other sessions
                model.Maximize(sum(other_assignments.values()) * 1000 +  # Primary: schedule all sessions
                               sum(time_preference_terms)  # Secondary: time preferences
                               )
                solver = cp_model.CpSolver()
                solver.parameters.num_search_workers = 8
                status = solver.Solve(model)

                if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    for key, var in other_assignments.items():
                        if solver.Value(var) == 1:
                            pending_saves.append({
                                'speciality': key[0],
                                'group': key[1],
                                'module_name': key[2],
                                'typeModule': key[3],
                                'section': section_name,
                                'professor_name': key[4],
                                'room_type': key[5],
                                'room_number': key[6],
                                'day': key[7],
                                'time': key[8],
                                'school_year': academic_year
                            })
                else:
                    print(f"❌ No feasible solution for other sessions in {speciality.name} {section_name}")

        with transaction.atomic():
            Schedule.objects.filter(speciality__in=specialities, school_year=academic_year,semester=semester,is_activated=True).delete()

            for entry in pending_saves:
                try:
                    module = Module.objects.get(specialityMod=entry['speciality'], module_name=entry['module_name'],
                                                semester=semester,is_activated=True)

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
                        school_year=entry['school_year'],
                        semester=semester
                    )
                except Exception as e:
                    print(f"Error saving schedule: {e}")

    except Exception as e:
        print(f"Error during generation: {e}")
