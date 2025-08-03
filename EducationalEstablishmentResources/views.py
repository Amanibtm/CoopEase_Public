from collections import defaultdict, OrderedDict
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from EducationalEstablishmentResources.models import Schedule, Module
from sharedResources.models import Department, TimeSlot
from users.models import Role, AdvancedUserProfile


@never_cache
@login_required
def showSchedule(request):
    # Calculate academic year
    today = date.today()
    year = today.year
    month = today.month

    if 6 <= month <= 12:
        academic_year = f"{year}/{year + 1}"
    else:
        academic_year = f"{year - 1}/{year}"

    day_order = {
        'SAMEDI': 0,
        'DIMANCHE': 1,
        'LUNDI': 2,
        'MARDI': 3,
        'MERCREDI': 4,
        'JEUDI': 5
    }

    if request.user.role == 'basicUser':
        try:
            user_profile = request.user.BasicUser_profile
            group_number = str(user_profile.group.group_number)
            speciality = user_profile.speciality

            # 1- Get all schedules for this department
            all_schedules = Schedule.objects.filter(
                speciality__level__departement=user_profile.speciality.level.departement,school_year=academic_year,
                is_activated=True).order_by('speciality', 'day', 'time')

            # 2- Figure out if semesters exist
            semesters_used = list(all_schedules.values_list('semester', flat=True).distinct())
            semesters_used = [s for s in semesters_used if s]
            has_semesters = any(s in ["s1", "s2"] for s in semesters_used)
            semesters = ["s1", "s2"] if has_semesters else ["Tous"]

            # 3- Setup dynamic containers (no need to predefine any keys)
            speciality_timetable = {sem: defaultdict(lambda: defaultdict(lambda: defaultdict(list))) for sem in semesters}
            group_timetable = {sem: defaultdict(lambda: defaultdict(list)) for sem in semesters}
            Departement_timetables = {sem: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))) for sem in semesters}

            # 4- Get time slots & days
            time_days = TimeSlot.objects.filter(departements=user_profile.speciality.level.departement).distinct()
            days = time_days.values_list('day__name', flat=True).distinct()

            # 5- Get section for group
            group_section = Schedule.objects.filter(
                speciality=speciality, group=group_number,school_year=academic_year,is_activated=True
            ).values_list('section', flat=True).first() or "Section1"

            # 6 -Get the two sub-sets for this user
            speciality_schedules = all_schedules.filter(speciality=speciality)
            group_schedules = all_schedules.filter(
                speciality=speciality).filter(Q(group=group_number) | Q(group="Tous", section=group_section))

            # 7 - Build speciality timetable
            for schedule in speciality_schedules:
                sem = schedule.semester if has_semesters else "Tous"
                day = schedule.day
                time_slot = schedule.time
                section = schedule.section

                speciality_timetable[sem][section][day][time_slot].append({
                    'module': schedule.module.module_name,
                    'mtype': schedule.typeModule,
                    'room': f"{schedule.room_type}{schedule.room_number}",
                    'professor': schedule.professor.user.first_name,
                    'group': schedule.group
                })

            # 8- Build group timetable
            for schedule in group_schedules:
                sem = schedule.semester if has_semesters else "Tous"
                day = schedule.day
                time_slot = schedule.time

                group_timetable[sem][day][time_slot].append({
                    'module': schedule.module.module_name,
                    'mtype': schedule.typeModule,
                    'room': f"{schedule.room_type}{schedule.room_number}",
                    'professor': schedule.professor.user.first_name,
                    'group': schedule.group,
                    'section': schedule.section
                })

            # 9- Build department timetable
            for schedule in all_schedules:
                sem = schedule.semester if has_semesters else "Tous"
                day = schedule.day
                time_slot = schedule.time
                section = schedule.section
                spec = schedule.speciality

                Departement_timetables[sem][spec][section][day][time_slot].append({
                    'module': schedule.module.module_name,
                    'mtype': schedule.typeModule,
                    'room': f"{schedule.room_type}{schedule.room_number}",
                    'professor': schedule.professor.user.first_name,
                    'group': schedule.group
                })

            # 10- Order by days
            ordered_speciality_timetable = {}
            ordered_group_timetable = {}
            ordered_Departement_timetable = {}

            for sem in semesters:
                # Speciality
                ordered_spec = {}
                for section, day_dict in speciality_timetable[sem].items():
                    ordered_day = OrderedDict()
                    for day in sorted(day_dict.keys(), key=lambda d: day_order.get(d, 99)):
                        ordered_day[day] = day_dict[day]
                    ordered_spec[section] = ordered_day
                ordered_speciality_timetable[sem] = ordered_spec

                # Group
                ordered_group = OrderedDict()
                for day in sorted(group_timetable[sem].keys(), key=lambda d: day_order.get(d, 99)):
                    ordered_group[day] = group_timetable[sem][day]
                ordered_group_timetable[sem] = ordered_group

                # Department
                ordered_dept = {}
                for spec, sections in Departement_timetables[sem].items():
                    ordered_sec = {}
                    for section, day_dict in sections.items():
                        ordered_day = OrderedDict()
                        for day in sorted(day_dict.keys(), key=lambda d: day_order.get(d, 99)):
                            ordered_day[day] = day_dict[day]
                        ordered_sec[section] = ordered_day
                    ordered_dept[spec] = ordered_sec
                ordered_Departement_timetable[sem] = ordered_dept


            # ⏰ Time slots
            time_slots = [slot.strftime("%H:%M") for slot in time_days.values_list('start_time', flat=True).distinct().order_by('start_time')]

            context = {
                'speciality': speciality,
                'speciality_timetable': {
                    sem: {section: dict(days) for section, days in ordered_speciality_timetable[sem].items()}
                    for sem in semesters
                },
                'group_timetable': {
                    sem: dict(ordered_group_timetable[sem])
                    for sem in semesters
                },
                'Departement_timetable': {
                    sem: {
                        speciality: {section: dict(days) for section, days in sections.items()}
                        for speciality, sections in ordered_Departement_timetable[sem].items()
                    } for sem in semesters
                },
                'time_slots': time_slots,
                'semesters': semesters,
                'has_semesters': has_semesters,
                'user': request.user,
                'view_type': 'student',
                'academic_year': academic_year
            }

            return render(request, 'EducationalEstablishment/scheduleDisplay.html', context)

        except AttributeError:
            pass

    return redirect('login')


@never_cache
@login_required
def enseignantsSchedules(request):
    # Calculate academic year
    today = date.today()
    year = today.year
    month = today.month

    if 6 <= month <= 12:
        academic_year = f"{year}/{year + 1}"
    else:
        academic_year = f"{year - 1}/{year}"

    day_order = {
        'SAMEDI': 0,
        'DIMANCHE': 1,
        'LUNDI': 2,
        'MARDI': 3,
        'MERCREDI': 4,
        'JEUDI': 5
    }

    if request.user.role == 'advancedUser':

        try:
            user_profile = request.user.Advanceduser_profile
            departements = Department.objects.filter(
                id__in=user_profile.modules.values_list('specialityMod__level__departement__id', flat=True),est=user_profile.est).distinct()
            time_days = TimeSlot.objects.filter(departements__in=departements).distinct()
            days = time_days.values_list('day__name', flat=True).distinct()

            # Get all schedules for professor's department
            all_schedules = Schedule.objects.filter(speciality__level__departement__in=departements,
                school_year=academic_year,is_activated=True).order_by('speciality', 'day', 'time')

            # Figure out if semesters exist
            semesters_used = list(all_schedules.values_list('semester', flat=True).distinct())
            semesters_used = [s for s in semesters_used if s]
            has_semesters = any(s in ["s1", "s2"] for s in semesters_used)
            semesters = ["s1", "s2"] if has_semesters else ["Tous"]

            # Setup timetable structures
            timetable = {sem: defaultdict(lambda: defaultdict(list)) for sem in semesters}
            Departement_timetables = {
                sem: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))) for sem in
                semesters}

            # Build professor's timetable
            if departements.exists():
                schedules = Schedule.objects.filter(
                    professor=user_profile,
                    school_year=academic_year,
                    is_activated=True
                ).order_by('day', 'time')

                for schedule in schedules:
                    sem = schedule.semester if has_semesters else "Tous"
                    day = schedule.day
                    time_slot = schedule.time

                    timetable[sem][day][time_slot].append({
                        'module': schedule.module.module_name,
                        'mtype': schedule.typeModule,
                        'speciality': schedule.speciality,
                        'room': f"{schedule.room_type}{schedule.room_number}",
                        'professor': schedule.professor.user.first_name,
                        'group': schedule.group,
                        'section': schedule.section
                    })

            # Build department timetable
            for schedule in all_schedules:
                sem = schedule.semester if has_semesters else "Tous"
                day = schedule.day
                time_slot = schedule.time
                section = schedule.section
                speciality = schedule.speciality

                Departement_timetables[sem][speciality][section][day][time_slot].append({
                    'module': schedule.module.module_name,
                    'mtype': schedule.typeModule,
                    'room': f"{schedule.room_type}{schedule.room_number}",
                    'professor': schedule.professor.user.first_name,
                    'group': schedule.group
                })

            # Order by days
            ordered_timetable = {}
            ordered_Departement_timetable = {}

            for sem in semesters:
                # Professor's timetable
                ordered_prof = OrderedDict()
                for day in sorted(timetable[sem].keys(), key=lambda d: day_order.get(d, 99)):
                    ordered_prof[day] = timetable[sem][day]
                ordered_timetable[sem] = ordered_prof

                # Department timetable
                ordered_dept = {}
                for speciality, sections in Departement_timetables[sem].items():
                    ordered_sec = {}
                    for section, day_dict in sections.items():
                        ordered_day = OrderedDict()
                        for day in sorted(day_dict.keys(), key=lambda d: day_order.get(d, 99)):
                            ordered_day[day] = day_dict[day]
                        ordered_sec[section] = ordered_day
                    ordered_dept[speciality] = ordered_sec
                ordered_Departement_timetable[sem] = ordered_dept

            # Time slots
            time_slots = [slot.strftime("%H:%M") for slot in
                          time_days.values_list('start_time', flat=True).distinct().order_by('start_time')]

            context = {
                'timetable': {
                    sem: dict(days)
                    for sem, days in ordered_timetable.items()
                },
                'all_timetable': {
                    sem: {
                        speciality: {section: dict(days) for section, days in sections.items()}
                        for speciality, sections in ordered_Departement_timetable[sem].items()
                    } for sem in semesters
                },
                'time_slots': time_slots,
                'semesters': semesters,
                'has_semesters': has_semesters,
                'user': request.user,
                'view_type': 'professor',
                'academic_year': academic_year
            }

            return render(request, 'EducationalEstablishment/enseignantsSchedules.html', context)

        except AttributeError:
            return redirect('login')


@never_cache
@login_required
def ViewModules(request):
    if request.user.role in ['advancedUser', 'basicUser']:
        try:
            # 🎓 Modules for this user
            if request.user.role == 'basicUser':
                user_profile = request.user.BasicUser_profile
                modules = Module.objects.filter(specialityMod=user_profile.speciality,is_activated=True)
            else:
                user_profile = request.user.Advanceduser_profile
                if not user_profile.Role or user_profile.Role.name != 'Responsable':
                    modules = user_profile.modules.all()
                else:
                    modules = Module.objects.filter(specialityMod__level__departement=user_profile.Role.departement)

            # 🎓 Detect semesters
            semesters_used = list(modules.values_list('semester', flat=True).distinct())
            semesters_used = [s for s in semesters_used if s]
            has_semesters = any(s in ["s1", "s2"] for s in semesters_used)
            semesters = ["s1", "s2"] if has_semesters else ["Tous"]

            # 🎓 Organize modules by semester
            semester_modules = {sem: defaultdict(list) for sem in semesters}

            for module in modules:
                sem = module.semester if has_semesters and module.semester in ["s1", "s2"] else "Tous"
                enseignants = AdvancedUserProfile.objects.filter(modules=module)
                semester_modules[sem][module] = list(enseignants)

            # 🎓 Final context (convert defaultdicts to dicts)
            context = {
                'module_enseignants': {
                    sem: dict(mods)
                    for sem, mods in semester_modules.items()
                },
                'semesters': semesters,
                'has_semesters': has_semesters,
            }

            return render(request, 'EducationalEstablishment/viewModules.html', context)

        except AttributeError:
            pass

    return render(request, 'unauthorized.html', {'message': "Profil utilisateur introuvable."})
