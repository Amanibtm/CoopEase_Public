from django import forms
from django.contrib.auth.forms import AuthenticationForm
from bootstrap_datepicker_plus.widgets import DatePickerInput  # Use this if you have it installed

from sharedResources.models import Department
from .models import GroupPreference, busyTimeSelect, Absence
from EducationalEstablishmentResources.models import Group, Space, Day, TimeSlot, Schedule
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom Utilisateur'}), label="")
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'}), label="")


# 1. Formulaire pour réserver un groupe (BasicUser)
class GroupPreferenceForm(forms.ModelForm):
    class Meta:
        model = GroupPreference
        fields = ['chosenGroup']
        widgets = {
            'chosenGroup': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'chosenGroup': "Choisissez votre groupe"
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and hasattr(self.user, 'BasicUser_profile'):
            # Filter groups by user's speciality
            self.fields['chosenGroup'].queryset = Group.objects.filter(speciality=self.user.BasicUser_profile.speciality)




# 2. Formulaire pour sélectionner des créneaux d’indisponibilité (AdvancedUser)
class BusyTimeSelectForm(forms.ModelForm):
    class Meta:
        model = busyTimeSelect
        fields = ['busyday', 'busytime']
        widgets = {
            'busyday': forms.Select(attrs={'class': 'form-control','required': 'required'}),
            'busytime': forms.CheckboxSelectMultiple(attrs={'class': 'time-checkboxes'})
        }
        labels = {
            'busyday': "Jour d'indisponibilité",
            'busytime': "Créneaux horaires"
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user.Advanceduser_profile:
            # Get all departments the user belongs to
            user_departements = Department.objects.filter(id__in=self.user.Advanceduser_profile.modules.values_list('specialityMod__level__departement__id', flat=True)
            ).distinct()
            # Filter timeslots by user's departments only
            self.fields['busytime'].queryset = TimeSlot.objects.filter(departements__in=user_departements).distinct() # distinct is to avoid repetitions

            # Days are not department-specific in your case
            time_days = TimeSlot.objects.filter(departements__in=user_departements).distinct()

            days = Day.objects.filter(id__in=time_days.values_list('day', flat=True))

            self.fields['busyday'].queryset = days

# 3. Formulaire d’annonce d’absence (AdvancedUser)


class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ['is_absent', 'date', 'absent_times']
        widgets = {
            'is_absent': forms.CheckboxInput(attrs={'class': 'time-checkboxes'}),
            # Replaced CheckboxSelectMultiple with DatePickerInput for date selection
            'date': DatePickerInput(options={
                "format": "DD/MM/YYYY",
                "locale": "fr",
                "showClose": True,
                "showClear": True,
                "showTodayButton": True,
            }),
            'absent_times': forms.CheckboxSelectMultiple(attrs={'class': 'time-checkboxes'}),
        }
        labels = {
            'is_absent': "Déclarer une absence",
            'date': "Date d'absence",
            'absent_times': "Créneaux horaires"
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and hasattr(self.user, 'Advanceduser_profile'):
            # Get all departments the user belongs to
            user_departements = Department.objects.filter(
                id__in=self.user.Advanceduser_profile.modules.values_list('specialityMod__level__departement__id', flat=True)
            ).distinct()
            # Filter timeslots by user's departments only
            self.fields['absent_times'].queryset = TimeSlot.objects.filter(departements__in=user_departements).distinct()

