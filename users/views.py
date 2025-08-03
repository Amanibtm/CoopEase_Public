import json
import traceback
from dateutil.parser import parse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from .models import *
from django.utils import timezone
from datetime import timedelta, date, datetime
from .forms import *
from django.shortcuts import get_object_or_404

@never_cache
def contact_superuser(request):
    User = get_user_model()
    superadmins = User.objects.filter(is_superuser=True)
    if not superadmins.exists():
        superadmins = []  # Handle case where no superusers exist

    return render(request, 'Users/contact_superuser.html', {
        'superadmins': superadmins
    })
@never_cache
def Login(request):

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password) #this function checks the database for a user with that username and password.
            if user is not None:
                login(request, user)
                # Redirect user based on role
                if user.role == 'basicUser':
                    return redirect('homepageBasicuser') #homepageBasicuser
                elif user.role == 'advancedUser':
                    return redirect('homepageAdvuser')

    else:
        form = LoginForm()

    return render(request, 'Users/login.html', {'form': form})


@never_cache
def Logout(request):
    logout(request)  # This clears the session and request.user
    response = redirect('login')
    return response


@never_cache  #view will not keep showing its content after logging out
@login_required
def homepage_advuser(request):
    return render(request, 'Users/homepage_advuser.html')

@never_cache
@login_required
def homepage_basicuser(request):
    return render(request, 'Users/homepage_basicuser.html')



@never_cache
@login_required
def book_group(request):
    user_profile = request.user.BasicUser_profile
    preference, created = GroupPreference.objects.get_or_create(user=user_profile)
    now = timezone.now()

    # L'utilisateur a déjà choisi un groupe
    if preference.chosenGroup:
        time_diff = now - preference.updated_at

        if request.method == 'POST':
            if 'cancel' in request.POST:
                if time_diff >= timedelta(hours=24):
                    preference.chosenGroup = None
                    preference.save()
                    return render(request, 'Users/book_group.html', {
                        'form': GroupPreferenceForm(instance=preference, user=request.user),
                        'success': "L'annulation a été effectuée avec succès."
                    })
                else:
                    wait_hours = 24 - time_diff.total_seconds() // 3600
                    return render(request, 'Users/book_group.html', {
                        'form': GroupPreferenceForm(instance=preference, user=request.user),
                        'error': f"Vous devez attendre encore {int(wait_hours)}h avant d'annuler."
                    })

            elif 'submit' in request.POST:
                if preference.chosenGroup is not None:
                    if time_diff >= timedelta(hours=48):
                        form = GroupPreferenceForm(request.POST, instance=preference, user=request.user)
                        if form.is_valid():
                            form.save()
                            return render(request, 'Users/book_group.html', {
                                'form': GroupPreferenceForm(instance=preference, user=request.user),
                                'success': "L'opération a été effectuée avec succès, Votre demande est en attente d'approbation."
                            })
                    else:
                        wait_hours = 48 - time_diff.total_seconds() // 3600
                        return render(request, 'Users/book_group.html', {
                            'form': GroupPreferenceForm(instance=preference, user=request.user),
                            'error': f"Vous devez attendre encore {int(wait_hours)}h avant d'inscrire à nouveau."
                        })
                else:
                    return render(request, 'Users/book_group.html', {
                        'form': GroupPreferenceForm(instance=preference, user=request.user),
                        'error': "Vous êtes déjà inscrit à un groupe. Veuillez annuler d’abord."
                    })
        else:
            form = GroupPreferenceForm(instance=preference, user=request.user)

    else:
        # Première réservation
        if request.method == 'POST':
            form = GroupPreferenceForm(request.POST, instance=preference, user=request.user)
            if form.is_valid() and preference.chosenGroup is not None:
                form.save()
                return render(request, 'Users/book_group.html', {
                    'form': form,
                    'success': "L'opération a été effectuée avec succès, Votre demande est en attente d'approbation."})
            else:
                return render(request, 'Users/book_group.html', {
                    'form': form,
                    'error': "Vous devez sélectionner un groupe."
                })
        else:
            form = GroupPreferenceForm(instance=preference, user=request.user)

    return render(request, 'Users/book_group.html', {'form': form})



@never_cache
@login_required
def book_space(request):
    print("➡️ Received request:", request.POST)
    try:
        user_profile = request.user.Advanceduser_profile
    except AttributeError:
        return redirect('login')

    today = date.today()
    year = today.year
    month = today.month

    if 6 <= month <= 12:
        academic_year = f"{year}/{year + 1}"
    else:
        academic_year = f"{year - 1}/{year}"

    try:
        semestresFixed=TargetedPublic.objects.filter(name=user_profile.est.name,systemSemestre=True).first()
        if semestresFixed:
            if semestresFixed.debutsemestre and semestresFixed.finsemestre:
                if semestresFixed.debutsemestre <= today < semestresFixed.finsemestre:
                    semestre='s1'
                elif semestresFixed.finsemestre <= today:
                    semestre='s2'
            else:
                if 6 <= month <= 12:
                    semestre = 's1'
                else:
                    semestre = 's2'
        else:
            semestre = None

    except TargetedPublic.DoesNotExist:
        semestre = None

    user_departments = Department.objects.filter(id__in=user_profile.modules.values_list('specialityMod__level__departement__id', flat=True)
    ).distinct()
    busy_schedule = Schedule.objects.filter(school_year=academic_year,is_activated=True,semester=semestre).values_list('room_number', 'room_type', 'day', 'time').distinct()
    spaces = Space.objects.filter(departements__in=user_departments).order_by('room_type', 'room_number').distinct()
    times = TimeSlot.objects.filter(departements__in=user_departments).distinct()
    days = times.values_list('day__name', flat=True).distinct()
    modules = user_profile.modules.all()



    now = timezone.now()
    today = now.date()
    current_time = now.time()
    SpacePreference.objects.filter(reservation_date=today, time__start_time__lte=current_time).delete()
    user_departments = Department.objects.filter(
        id__in=user_profile.modules.values_list('specialityMod__level__departement__id', flat=True)
    ).distinct()
    schedule_data = {"Always": []}

    for day in days:
        for time in times:
            for space in spaces:
                is_busy = (space.room_number, space.room_type.name, day, time.start_time.strftime('%H:%M')) in busy_schedule
                if not is_busy:
                    Daay = Day.objects.get(name=day)
                    reservations = SpacePreference.objects.filter(chosenSpace=space, day=Daay, time=time).distinct()
                    # Prepare unavailable dates as strings with user info
                    unavailable_dates = []
                    for d in reservations:
                        if d.user == user_profile:
                            status = f"{d.reservation_date.strftime('%d-%m-%Y')} (Votre réservation{' - En attente' if not d.is_approved else ''})"
                            unavailable_dates.append(status)
                        else:
                            unavailable_dates.append(d.reservation_date.strftime('%d-%m-%Y'))

                    schedule_data["Always"].append({
                        "space": space,
                        "day": day,
                        "time": time.start_time.strftime('%H:%M'),
                        "unavailable_dates": ' '.join(unavailable_dates),
                        "unavailable_dates_list": unavailable_dates  # For JavaScript
                    })
    day_order = {
        'SAMEDI': 0,
        'DIMANCHE': 1,
        'LUNDI': 2,
        'MARDI': 3,
        'MERCREDI': 4,
        'JEUDI': 5
    }
    schedule_data["Always"].sort(
        key=lambda x: (day_order.get(x["day"], 99), x["time"])
    )

    if request.method == 'POST':
        space_id = request.POST.get('space')
        day_name = request.POST.get('day')
        time_str = request.POST.get('time')
        module_id = request.POST.get('module')
        module_type = request.POST.get('module_type')
        group = request.POST.get('group')
        section = request.POST.get('section')
        reservation_date_str = request.POST.get('reservation_date')
        print(f"module_type: {module_type}, group: {group}")  # Specific debug


        space = Space.objects.get(id=space_id)
        day = Day.objects.get(name=day_name)
        time = TimeSlot.objects.filter(
            start_time=datetime.datetime.strptime(time_str, '%H:%M').time(),departements__in=user_departments).distinct().first()
        reservation_date = datetime.datetime.strptime(reservation_date_str, '%Y-%m-%d').date()

        semestresFixed = TargetedPublic.objects.filter(name=user_profile.est.name, systemSemestre=True).first()
        if semestresFixed:
            months6_coming = semestresFixed.finsemestre + timedelta(weeks=24) # +6mois

            if semestre == 's1' and not (semestresFixed.debutsemestre <= reservation_date < semestresFixed.finsemestre):
                return JsonResponse({
                    'status': 'danger',
                    'message': "Veuillez sélectionner une date comprise dans la durée du semestre 1.",
                    'source': 'book_space'
                })
            if semestre == 's2' and not (semestresFixed.finsemestre <= reservation_date < months6_coming):
                return JsonResponse({
                    'status': 'danger',
                    'message': "Veuillez sélectionner une date comprise dans la durée du semestre 2.",
                    'source': 'book_space'
                })

        # Validate module
        if not module_id:
            return JsonResponse({
                'status': 'danger',
                'message': "Veuillez sélectionner un module.",
                'source': 'book_space'
            })

        try:
            module = Module.objects.get(id=module_id)
        except module.DoesNotExist:
            return JsonResponse({
                'status': 'danger',
                'message': "Module invalide.",
                'source': 'book_space'
            })

        # Check if module belongs to user
        if module not in user_profile.modules.all():
            return JsonResponse({
                'status': 'danger',
                'message': "Vous n'êtes pas autorisé à réserver pour ce module.",
                'source': 'book_space'
            })

        module = Module.objects.get(id=module_id)
        schedule_spc = (Schedule.objects.filter(speciality=module.specialityMod, section=f"Section{section}",
                                                group=group, day=day_name, time=time_str,school_year=academic_year,
                                                is_activated=True,semester=semestre).distinct()
                        or Schedule.objects.filter(speciality=module.specialityMod, section=f"Section{section}",
                                                   group="Tous", day=day_name, time=time_str,school_year=academic_year,
                                                   is_activated=True,semester=semestre).distinct())
        if schedule_spc.exists():
            return JsonResponse({
                'status': 'danger',
                'message': f"Le groupe({group}) de cette section a une séance le {day_name} à {time_str}." ,
                'source': 'book_space'
            })

        if module_type == 'Cours':
            if module.nbrCoursSemaine==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"il n'y a pas de {module_type} dans ce module.",
                    'source': 'book_space'
                })
        elif module_type == 'TD':
            if module.nbrTDSemaine==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"il n'y a pas de {module_type} dans ce module.",
                    'source': 'book_space'
                })
        elif module_type == 'TP':
            if module.nbrTPSemaine==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"il n'y a pas de {module_type} dans ce module.",
                    'source': 'book_space'
                })

        doubled = SpacePreference.objects.filter(chosenSpace=space, day=day, time=time, reservation_date=reservation_date).exists()
        print("CHECKING IF ALREADY RESERVED:", doubled)

        if doubled:
            print("\nChecking reservation for:", space, day, time, reservation_date)
            return JsonResponse({
                'status': 'danger',
                'message': "Date déjà réservée. ",
                'source': 'book_space'
            })

        prof_multiple_seances_in_an_hour = SpacePreference.objects.filter(user=user_profile, day=day, time=time, reservation_date=reservation_date).exists()
        if prof_multiple_seances_in_an_hour:
            return JsonResponse({
                'status': 'danger',
                'message': "Vous ne pouvez pas réserver plus d'une fois le même jour et à la même heure.",
                'source': 'book_space'
            })

        groups = re.split(r"[ ,./@#$%^&*()_+=|?><:;'\"]+", group.strip())
        for group in groups:
            if group.isdigit():
                group_number = int(group)
                groupe_exists=Group.objects.filter(speciality=module.specialityMod,section=section,group_number=group_number).exists()
                if not groupe_exists:
                    return JsonResponse({
                        'status': 'danger',
                        'message': f"Ce groupe n'existe pas dans la specialité {module.specialityMod}",
                        'source': 'book_space'
                    })
        else:
            if not module.specialityMod.sections >= int(section) or section==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"Cette section n'existe pas dans la specialité {module.specialityMod}",
                    'source': 'book_space'
                })


        #Reservation Limits Check
        week_ago = timezone.now() - timedelta(weeks=1)
        user_reservations = SpacePreference.objects.filter(user=user_profile, timestamp__gte=week_ago).distinct()

        if user_reservations.count() >= 5:
            return JsonResponse({'status': 'danger', 'message': "Vous avez atteint le nombre maximum de réservations (5) pour cette semaine.",'source': 'book_space'})

        if reservation_date < today:
            return JsonResponse({'status': 'danger', 'message': "La date sélectionnée est déjà expirée.",'source': 'book_space'})

        else:
            groups_string = ", ".join(groups)

            SpacePreference.objects.create(
                user=user_profile,
                chosenSpace=space,
                chosenModule=module,
                Modtype=module_type,
                group=groups_string,
                section=f"Section{section}",
                day=day,
                time=time,
                reservation_date=reservation_date
            )
            # Get the updated count
            new_count = SpacePreference.objects.filter(user=user_profile, timestamp__gte=week_ago).count()
            return JsonResponse({'status': 'success', 'message': "Votre réservation a été enregistrée avec succès !", 'new_count': new_count,'source': 'book_space'})

    return render(request, 'Users/book_space.html', {'schedule_data': schedule_data, 'modules': modules, 'schedule_json': json.dumps([
        {
            "space_id": entry["space"].id,
            "room_type": entry["space"].room_type.name,
            "room_number": entry["space"].room_number,
            "day": entry["day"],
            "time": entry["time"],
            "unavailable_dates": entry["unavailable_dates"],
            "unavailable_dates_list": entry["unavailable_dates_list"]  # for js

        }
        for entry in schedule_data["Always"]
        ])})



@never_cache
@login_required
def book_occasionaly_available_space(request):
    try:
        user_profile = request.user.Advanceduser_profile
    except AttributeError:
        return redirect('login')

    today = date.today()
    year = today.year
    month = today.month

    if 6 <= month <= 12:
        academic_year = f"{year}/{year + 1}"
    else:
        academic_year = f"{year - 1}/{year}"

    try:
        semestresFixed=TargetedPublic.objects.get(name=user_profile.est.name,systemSemestre=True)
        if semestresFixed:
            if semestresFixed.debutsemestre and semestresFixed.finsemestre:
                if semestresFixed.debutsemestre <= today < semestresFixed.finsemestre:
                    semestre='s1'
                elif semestresFixed.finsemestre <= today:
                    semestre='s2'
            else:
                if 6 <= month <= 12:
                    semestre = 's1'
                else:
                    semestre = 's2'
        else:
            semestre = None

    except TargetedPublic.DoesNotExist:
        semestre = None


    # Current Date and Time
    now = timezone.now()
    today = now.date()
    current_time = now.time()

    # Auto-delete expired reservations
    SpacePreference.objects.filter(reservation_date=today, time__start_time__lte=current_time).delete()
    Absence.objects.annotate(max_time=Max('absent_times__start_time')).filter(
        Q(date__lt=today) |  # Date is before today OR
        Q(date=today, max_time__lte=current_time)  # Today but all times passed
    ).delete()
    user_departments = Department.objects.filter(
        id__in=user_profile.modules.values_list('specialityMod__level__departement__id', flat=True),
        est=user_profile.est).distinct()
    schedule_data = {"Occasional": []}

    #Occasional availability based on Absences
    absences = Absence.objects.filter(is_absent=True, user__modules__specialityMod__level__departement__in=user_departments).distinct()
    #prof's modules
    modules = user_profile.modules.all()
    for absence in absences:
        # Get the professor's schedules
        schedules = Schedule.objects.filter(professor=absence.user,school_year=academic_year,is_activated=True,semester=semestre).distinct()
        french_days = {
            'Monday': 'LUNDI',
            'Tuesday': 'MARDI',
            'Wednesday': 'MERCREDI',
            'Thursday': 'JEUDI',
            'Friday': 'VENDREDI',
            'Saturday': 'SAMEDI',
            'Sunday': 'DIMANCHE'
        }
        english_day = absence.date.strftime('%A')
        day_name = french_days.get(english_day, english_day.upper())

        # Loop through all absent days and times for this user
        for time in absence.absent_times.all():
            # Filter the professor's schedule matching the day and time
            matching_schedules = schedules.filter(day=day_name,time=time.start_time.strftime('%H:%M'),
                                                    speciality__level__departement__in=user_departments,
                                                    school_year=academic_year,is_activated=True,semester=semestre)
            for schedule in matching_schedules:
                try:
                    space = Space.objects.get(room_type__name=schedule.room_type, room_number=schedule.room_number)
                    Daay = Day.objects.get(name=day_name)

                    reservations = SpacePreference.objects.filter(chosenSpace=space, reservation_date=absence.date, day=Daay, time=time)
                    if reservations:
                        status="Réservé"
                    else:
                        status="Disponible"
                    schedule_data["Occasional"].append({
                        "space": space,
                        "date": absence.date,
                        "day": day_name,
                        "time": time.start_time.strftime('%H:%M'),
                        "status": status
                    })
                except Space.DoesNotExist:
                    print(f"Aucun espace correspondant trouvé pour {schedule.room_type.name} - {schedule.room_number}")
    #Handle Reservation Logic
    if request.method == 'POST':
        space_id = request.POST.get('space')
        day_name = request.POST.get('day')
        time_str = request.POST.get('time')
        date_ = request.POST.get('date')
        module_id = request.POST.get('module')
        module_type = request.POST.get('module_type')
        group = request.POST.get('group')
        section = request.POST.get('section')


        # 🎯 Validation
        space = Space.objects.get(id=space_id)
        day = Day.objects.get(name=day_name)
        time = TimeSlot.objects.filter(
            start_time=datetime.datetime.strptime(time_str, '%H:%M').time(), departements__in=user_departments).first()
        try:
            # Automatically detect the date format and parse it correctly
            print(f"🔍 Debug: date recoit en string -> {date_}")
            date__ = parse(date_).date()
            print(f"✅ Date: {date__}")
        except ValueError as e:
            print('Format de date non reconnu.')
            traceback.print_exc()
            return JsonResponse({'status': 'danger', 'message': "Format de date non reconnu.",'source': 'book_occasional'})

        if not module_id:
            return JsonResponse({
                'status': 'danger',
                'message': "Veuillez sélectionner un module.",
                'source': 'book_occasional'
            })

        try:
            module = Module.objects.get(id=module_id)
        except Module.DoesNotExist:
            return JsonResponse({
                'status': 'danger',
                'message': "Module invalide.",
                'source': 'book_occasional'
            })

        #check if group-section already have a session in the selected day-time
        module = Module.objects.get(id=module_id)
        schedule_spc = (Schedule.objects.filter(speciality=module.specialityMod, section=f"Section{section}",
                                               group=group, day=day_name, time=time_str,school_year=academic_year,
                                                is_activated=True,semester=semestre)
                        or Schedule.objects.filter(speciality=module.specialityMod, section=f"Section{section}",
                                               group="Tous", day=day_name, time=time_str,school_year=academic_year,
                                                   is_activated=True,semester=semestre))
        print(schedule_spc)
        if schedule_spc.exists():
            return JsonResponse({
                'status': 'danger',
                'message': f"Le groupe({group}) de cette section a une séance le {day_name} à {time_str}.",
                'source': 'book_occasional'
            })


        if module_type == 'Cours':
            if module.nbrCoursSemaine==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"il n'y a pas de {module_type} dans ce module.",
                    'source': 'book_space'
                })
        elif module_type == 'TD':
            if module.nbrTDSemaine==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"il n'y a pas de {module_type} dans ce module.",
                    'source': 'book_space'
                })
        elif module_type == 'TP':
            if module.nbrTPSemaine==0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"il n'y a pas de {module_type} dans ce module.",
                    'source': 'book_space'
                })


        # Check if module belongs to user
        if module not in user_profile.modules.all():
            return JsonResponse({
                'status': 'danger',
                'message': "Vous n'êtes pas autorisé à réserver pour ce module.",
                'source': 'book_occasional'
            })

        prof_multiple_seances_in_an_hour = SpacePreference.objects.filter(user=user_profile, day=day, time=time,
                                                                          reservation_date=date__).exists()
        if prof_multiple_seances_in_an_hour:
            return JsonResponse({
                'status': 'danger',
                'message': "Vous ne pouvez pas réserver plus d'une fois le même jour et à la même heure.",
                'source': 'book_occasional'
            })

        groups = re.split(r"[ ,./@#$%^&*()_+=|?><:;'\"]+", group.strip())
        print(group)

        for group in groups:
            if group.isdigit():
                group_number = int(group)
                groupe_exists = Group.objects.filter(speciality=module.specialityMod, section=section,
                                                     group_number=group_number).exists()
                if not groupe_exists:
                    return JsonResponse({
                        'status': 'danger',
                        'message': f"Ce groupe n'existe pas dans la specialité {module.specialityMod}",
                        'source': 'book_space'
                    })
        else:
            if not module.specialityMod.sections >= int(section) or section == 0:
                return JsonResponse({
                    'status': 'danger',
                    'message': f"Cette section n'existe pas dans la specialité {module.specialityMod}",
                    'source': 'book_space'
                })

        #reservation limits check
        week_ago = timezone.now() - timedelta(weeks=1)
        user_reservations = SpacePreference.objects.filter(user=user_profile, timestamp__gte=week_ago)
        if user_reservations.count() >= 5:
            return JsonResponse({'status': 'danger', 'message': "Vous avez atteint le nombre maximum de réservations (5) pour cette semaine.",'source': 'book_occasional'})

        # 🎯 Time Validation
        if date__ < today:
            return JsonResponse({'status': 'danger', 'message': "La date sélectionnée est déjà expirée.",'source': 'book_occasional'})
        else:
            # ✅ Create the reservation
            groups_string = ", ".join(groups)
            SpacePreference.objects.create(
                user=user_profile,
                chosenSpace=space,
                chosenModule=module,
                Modtype=module_type,
                group=groups_string,
                section=f"Section{section}",
                day=day,
                time=time,
                reservation_date=date__
            )
            new_count = SpacePreference.objects.filter(user=user_profile, timestamp__gte=week_ago).count()
            return JsonResponse({'status': 'success', 'message': "Votre réservation a été enregistrée avec succès !",
                                 'new_count': new_count,'source': 'book_occasional'})

    return render(request, 'Users/book_occ_space.html', {'schedule_data': schedule_data, 'modules': modules})


@never_cache
@login_required
def select_busy_time(request):


    if not request.user.is_authenticated:
        print("USER IS NOT AUTHENTICATED")
        return redirect('login')
    try:
        user_profile = request.user.Advanceduser_profile
    except AttributeError:
        return redirect('login')  # Or handle unauthorized access

    # deleting approved busy times
    months3_ago = timezone.now() - timedelta(weeks=12)
    busyTimeSelect.objects.filter(user=user_profile, timestamp__lte=months3_ago, is_approved=True).delete()
    # deleting non approved busy times
    month_ago = timezone.now() - timedelta(weeks=1)
    busyTimeSelect.objects.filter(user=user_profile, timestamp__lte=month_ago, is_approved=False).delete()

    previous_entries = busyTimeSelect.objects.filter(user=user_profile).prefetch_related('busytime', 'busyday')

    if request.method == 'POST':
        form = BusyTimeSelectForm(request.POST, user=request.user)

        if form.is_valid():
            busy_day = form.cleaned_data.get('busyday')

            # Check if there is already a record for the same day
            existing_entry = busyTimeSelect.objects.filter(user=user_profile, busyday=busy_day).first()

            # If it exists, update it, otherwise create a new one
            if existing_entry:
                existing_entry.busytime.set(form.cleaned_data['busytime'])  # Update the M2M field
                existing_entry.save()
                return render(request, 'Users/select_busy_time.html', {
                    'form': form,
                    'previous_entries': previous_entries,
                    'success': "Enregistrement mis à jour avec succès. "})
            else:
                busy_time = form.save(commit=False)
                busy_time.user = user_profile
                busy_time.save()
                form.save_m2m()# Save many-to-many relationships

                return render(request, 'Users/select_busy_time.html', {
                    'form': form,
                    'previous_entries': previous_entries,
                    'success': "Nouvel enregistrement affecté avec succès. "})
        else:
            return render(request, 'Users/select_busy_time.html', {
                'form':BusyTimeSelectForm(user=request.user),
                'previous_entries': previous_entries,
                'error': "Erreur lors de l'enregistrement."})
    else:
        form = BusyTimeSelectForm(user=request.user)
    previous_entries = busyTimeSelect.objects.filter(user=user_profile).prefetch_related('busytime', 'busyday')

    return render(request, 'Users/select_busy_time.html', {'form': form, 'previous_entries': previous_entries})


@never_cache
@login_required
def delete_busy_entry(request, entry_id):
    entry = get_object_or_404(busyTimeSelect, id=entry_id, user=request.user.Advanceduser_profile)
    entry.delete()
    return redirect('SelectBusyTime')  # Replace with your URL name


@never_cache
@login_required
def approve_reservations(request):
    try:
        user_profile = request.user.Advanceduser_profile
    except AttributeError:
        return redirect('login')

    #deleting approved busy times
    months3_ago = timezone.now() - timedelta(weeks=12)
    busyTimeSelect.objects.filter(timestamp__lte=months3_ago,is_approved=True).delete()
    #deleting non approved busy times
    month_ago = timezone.now() - timedelta(weeks=1)
    busyTimeSelect.objects.filter(timestamp__lte=month_ago,is_approved=False).delete()

    # Check if user is Responsable (you'll need to implement this logic)
    if user_profile.Role.name!='Responsable':  # You need to implement this function
        return redirect('homepageAdvuser')

    # Get unapproved reservations for the departments the Responsable manages
    user_department=user_profile.Role.departement
    pending_reservations = SpacePreference.objects.filter(is_approved=False,
        chosenSpace__departements=user_department).order_by('-timestamp')

    approved_reservations = SpacePreference.objects.filter(is_approved=True,
        chosenSpace__departements=user_department).order_by('-timestamp')

    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        action = request.POST.get('action')

        try:
            reservation = SpacePreference.objects.get(id=reservation_id)
            if action == 'approve':
                reservation.is_approved = True
                reservation.save()
                return JsonResponse({'status': 'success', 'message': 'Réservation approuvée avec succès!'})
            elif action == 'reject':
                reservation.delete()
                return JsonResponse({'status': 'success', 'message': 'Réservation rejetée avec succès!'})
            elif action == 'cancel':
                reservation.is_approved = False
                reservation.save()
                return JsonResponse({'status': 'success', 'message': 'Approbation annulée avec succès!'})
        except SpacePreference.DoesNotExist:
            return JsonResponse({'status': 'danger', 'message': 'Réservation introuvable!'})

    return render(request, 'Users/approve_reservations.html', {
        'pending_reservations': pending_reservations, 'approved_reservations': approved_reservations
    })


@never_cache
@login_required
def confirm_busy_times(request):
    try:
        user_profile = request.user.Advanceduser_profile
        responsible_dept = user_profile.Role.departement
    except AttributeError:
        return redirect('homepageAdvuser')
    all_busy_times = busyTimeSelect.objects.select_related('user', 'busyday') \
        .prefetch_related('busytime') \
        .filter(user__modules__specialityMod__level__departement=responsible_dept,user__est=responsible_dept.est).distinct() \
        .order_by('-timestamp')
    if request.method == "POST":
        busy_id = request.POST.get('busy_id')
        action = request.POST.get('action')

        if busy_id:
            busy_time = get_object_or_404(busyTimeSelect, id=busy_id)
            if action == "approve":
                busy_time.is_approved = True
                busy_time.save()
            elif action == "cancel":
                busy_time.is_approved = False
                busy_time.save()

    return render(request, 'Users/confirm_busy_times.html', {'all_busy_times': all_busy_times})

@never_cache
@login_required
def annonce_absence(request):
    try:
        user_profile = request.user.Advanceduser_profile
    except AttributeError:
        return redirect('login')  # Or handle unauthorized access

    existing_absences = Absence.objects.filter(user=user_profile).order_by('-date')

    if request.method == 'POST':
        form = AbsenceForm(request.POST, user=request.user)

        if form.is_valid():
            absent_date = form.cleaned_data.get('date')
            existing_entry = Absence.objects.filter(user=user_profile,date=absent_date).first()

            # If it exists, update it, otherwise create a new one

            if existing_entry:
                existing_entry.absent_times.set(form.cleaned_data['absent_times'])  # Update the M2M field
                existing_entry.save()
                return render(request, 'Users/annonce_absence.html', {
                    'form': form,
                    'existing_absences': existing_absences,
                    'success': "Votre déclaration d'absence a été mise à jour avec succès !"})

            else:
                absence = form.save(commit=False)  # save basic fields
                absence.user = user_profile  # link the logged-in advanced user
                absence.save()
                form.save_m2m()  # save many to many fields

                return render(request, 'Users/annonce_absence.html', {
                    'form': form,
                    'existing_absences': existing_absences,
                    'success': "Nouvelle déclaration d'absence a été enregistrée avec succès !"})

        else:
            return render(request, 'Users/annonce_absence.html', {
                'form': form,
                'existing_absences': existing_absences,
                'error': "Erreur lors de l'enregistrement."})

    else:
        # Try to get existing entry
        form = AbsenceForm(user=request.user)

    return render(request, 'Users/annonce_absence.html', {'form': form, 'existing_absences': existing_absences})


@never_cache
@login_required
def delete_absence(request, entry_id):
    entry = get_object_or_404(Absence, id=entry_id, user=request.user.Advanceduser_profile)
    entry.delete()
    return redirect('announceAbsence')  # Replace with your URL name


@never_cache
@login_required
def OperationsHistory(request):
    try:
        user_profile = request.user.Advanceduser_profile
    except AttributeError:
        return redirect('login')

    # 🎯 **Step 1:** Get all the user's operations
    operations = []

    # 🚀 1. Room Reservations
    for reservation in SpacePreference.objects.filter(user=user_profile):
        if reservation.is_approved==True:
            statut ='<span class="badge bg-success mt-2">✔️ Confirmé</span>'
        else:
            statut = '<span class="badge bg-warning text-dark mt-2">⏳ En attente</span>'
        operations.append({
        'type': "Réservation de Salle",
        'description': f"<strong> Salle réservé: </strong> {reservation.chosenSpace} <br> <strong>Date:</strong> {reservation.reservation_date} | <strong>Jour:</strong> {reservation.day}<br><strong>Heure:</strong> {reservation.time}<br><strong>Module:</strong> {reservation.chosenModule.module_name} | <strong>Type:</strong> {reservation.Modtype}<br> <strong>Groupe:</strong> {reservation.group} | <strong>Section:</strong> {reservation.section}<br> {statut}",
        'timestamp': reservation.timestamp,
        'id': reservation.id,
        'model': 'space'})

    # 🎯 **Step 2:** Sort operations by timestamp (newest first)
    operations.sort(key=lambda x: x['timestamp'], reverse=True)

    # 🎯 **Step 3:** Handle deletion with AJAX
    if request.method == 'POST':
        operation_id = request.POST.get('operation_id')
        model_type = request.POST.get('model_type')

        model_map = {
            'space': SpacePreference,
        }

        # 🚀 Get the correct model and delete the entry
        model = model_map.get(model_type)
        if model:
            model.objects.filter(id=operation_id).delete()
            return JsonResponse({'status': 'success'})

    return render(request, 'Users/operations_history.html', {'operations': operations})


@never_cache
@login_required
def tableauAffichage(request):
    try:
        user_profile = request.user.BasicUser_profile
    except AttributeError:
        return redirect('login')

    operations = []

    # 🚀 **1. Room Reservations (SpacePreference)**
    reservations = SpacePreference.objects.filter(chosenModule__specialityMod=user_profile.speciality, is_approved=True).distinct()

    for reservation in reservations:
        operations.append({
            'type': "Séance ajoutée",
            'speciality':reservation.chosenModule.specialityMod,
            'prof': f"{reservation.user.first_name} {reservation.user.last_name}",
            'space': f"{reservation.chosenSpace.room_number}  ({reservation.chosenSpace.room_type.name})",
            'date': reservation.reservation_date,
            'day': reservation.day.name,
            'time': reservation.time.start_time.strftime('%H:%M'),
            'module': f"{reservation.chosenModule.module_name} - {reservation.Modtype}",
            'group': reservation.group,
            'section': reservation.section,
            'timestamp': reservation.timestamp,
            'id': reservation.id,
            'model': 'space'
        })

    # 🚀 **2. Absences of professors teaching modules matching the BasicUser's speciality**
    absences = Absence.objects.filter(user__modules__specialityMod=user_profile.speciality).distinct()

    for absence in absences:
        absent_slots = ', '.join([t.start_time.strftime('%H:%M') for t in absence.absent_times.all()])
        operations.append({
            'type': "Absence",
            'prof': f"{absence.user.first_name} {absence.user.last_name}",
            'date': absence.date,
            'time': absent_slots,
            'timestamp': absence.timestamp,
            'id': absence.id,
            'model': 'absence'
        })

    # 🎯 **Step 2:** Sort operations by timestamp (newest first)
    operations.sort(key=lambda x: x['timestamp'], reverse=True)

    # 🎯 **Step 3:** Pass to template
    return render(request, 'Users/tableau_affichage.html', {'operations': operations})


@never_cache
@login_required
def profile(request):
    if request.user.role == 'advancedUser':
            user_profile = request.user.Advanceduser_profile
            return render(request, 'Users/profile.html', {'profile': user_profile})
    elif request.user.role == 'basicUser':
            user_profile = request.user.BasicUser_profile
            return render(request, 'Users/profile.html', {'profile': user_profile})
