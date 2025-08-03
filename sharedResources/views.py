from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from EducationalEstablishmentResources.models import Schedule, Module
from sharedResources.models import Space, Equipement, TimeSlot, Department
from users.models import AdvancedUserProfile


@never_cache
@login_required
def ViewSpaces(request):

    if request.user.role == 'advancedUser':
        user_profile = request.user.Advanceduser_profile
        departements = Department.objects.filter(id__in=user_profile.modules.values_list('specialityMod__level__departement__id', flat=True)
        ).distinct()
        spaces = Space.objects.filter(departements__in=departements)

    else:
        return render(request, 'unauthorized.html')

    spaceDepts = Department.objects.filter(Spacesdept__in=spaces).distinct()
    times = TimeSlot.objects.filter(departements__in=spaceDepts).distinct()
    days = times.values_list('day__name', flat=True).distinct()

    #load all scheduled (busy) room_number+room_type + day + time
    busy_schedule = Schedule.objects.values_list('room_number', 'room_type', 'day', 'time')

    schedule_data = []  # List of (day, time, [available_spaces])

    for day in days:
        for time in times:
            available_spaces = []
            for space in spaces:
                is_busy = (space.room_number, space.room_type.name, day, time.start_time.strftime('%H:%M')) in busy_schedule
                if not is_busy:
                    available_spaces.append(space)
            schedule_data.append((day, time, available_spaces))

    # Define custom order map
    day_order = {
        'SAMEDI': 0,
        'DIMANCHE': 1,
        'LUNDI': 2,
        'MARDI': 3,
        'MERCREDI': 4,
        'JEUDI': 5
    }

    # Sort the list based on custom day order, then by time
    schedule_data.sort(key=lambda x: (day_order.get(x[0], 99), x[1].start_time))

    return render(request, 'sharedResources/view_spaces.html', {
        'schedule_data': schedule_data
    })


@never_cache
@login_required
def ViewEquipements(request):

    try:
        if request.user.role == 'basicUser':
            user_profile = request.user.BasicUser_profile
            departement = user_profile.speciality.level.departement
            equipements = Equipement.objects.filter(departement=departement)

        elif request.user.role == 'advancedUser':
            user_profile = request.user.Advanceduser_profile
            departements = Department.objects.filter(id__in=user_profile.modules.values_list('specialityMod__level__departement__id', flat=True)
            ).distinct()
            equipements = Equipement.objects.filter(departement__in=departements).distinct()

        else:
            return render(request, 'unauthorized.html')
    except AttributeError:
        equipements = Equipement.objects.none()

    # Now using normal dictionaries
    equipment_data = {}

    for equip in equipements:
        dept_name = equip.departement.name
        equip_type = equip.type

        if dept_name not in equipment_data:
            equipment_data[dept_name] = {}

        if equip_type not in equipment_data[dept_name]:
            equipment_data[dept_name][equip_type] = []

        equipment_data[dept_name][equip_type].append(equip)

    context = {
        'equipment_data': equipment_data,
    }
    return render(request, 'sharedResources/view_equipments.html', context)

@never_cache
@login_required
def ViewAdvancedUsers(request):
    try:
        if request.user.role == 'basicUser':
            user_profile = request.user.BasicUser_profile
            speciality = user_profile.speciality
            speciality_ids = [speciality.id]

            # Get all modules for the speciality to determine semesters
            modules = Module.objects.filter(specialityMod__in=speciality_ids)

            # Determine which semesters exist
            semesters_used = list(modules.values_list('semester', flat=True).distinct())
            semesters_used = [s for s in semesters_used if s]
            has_semesters = any(s in ["s1", "s2"] for s in semesters_used)
            semesters = ["s1", "s2"] if has_semesters else ["Tous"]

            # Get all advanced users for the speciality
            advUsers = AdvancedUserProfile.objects.filter(modules__specialityMod__in=speciality_ids).distinct()

            # Organize users by semester and modules they teach
            users_data = {}
            for semester in semesters:
                users_data[semester] = []
                for user in advUsers:
                    # Get modules for this user in this semester
                    user_modules = user.modules.filter(specialityMod__in=speciality_ids,
                        semester=semester if has_semesters else None).distinct()

                    if user_modules.exists():
                        users_data[semester].append({
                            'user': user,
                            'modules': list(user_modules.values('module_name','specialityMod__name','specialityMod__level__name', 'semester'))
                        })

            context = {
                'users_data': users_data,
                'semesters': semesters,
                'has_semesters': has_semesters,
                'speciality': speciality
            }

            return render(request, 'sharedResources/view_advanced_users.html', context)

        elif request.user.role == 'advancedUser':
            user_profile = request.user.Advanceduser_profile
            departement_ids = list(
                user_profile.modules.values_list('specialityMod__level__departement__id', flat=True).distinct())

            advUsers = AdvancedUserProfile.objects.filter(
                modules__specialityMod__level__departement__id__in=departement_ids).distinct()

            users_data = {}
            for user in advUsers:
                user_departments = user.modules.values_list('specialityMod__level__departement__id',flat=True).distinct()
                for dep_id in user_departments:
                    if dep_id in departement_ids:
                        dep_name = Department.objects.get(pk=dep_id).name
                        users_data.setdefault(dep_name, []).append(user)

            return render(request, 'sharedResources/view_advanced_users.html', {'users_data': users_data})


    except AttributeError:

        return render(request, 'unauthorized.html', {

            'message': "Profil utilisateur introuvable."

        })

    return render(request, 'unauthorized.html')


