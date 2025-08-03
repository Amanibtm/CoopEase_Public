import re

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpResponse

import EducationalEstablishmentResources
from EducationalEstablishmentResources.models import Module, Speciality
from sharedResources.models import TargetedPublic, Space, TimeSlot, Department, Grade
from .models import User, Role, AdvancedUserProfile, BasicUserProfile, EstablishmentAdminProfile, \
    DepartementAdminProfile, GroupPreference, SpacePreference, busyTimeSelect, Absence
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

import pandas as pd
from django.shortcuts import redirect, render
from django.urls import path
from django import forms
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin

# Register your models here.

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField()


def get_filtered_queryset(request, model):
    """Returns a filtered queryset based on admin's scope"""
    if request.user.is_superuser:
        return model.objects.all()

    if request.user.role == 'est_admin':
        est = request.user.estAdminProfile.est
        if model == Speciality:
            return model.objects.filter(level__departement__est=est).distinct()
        elif model.__name__ == 'Group':
            return model.objects.filter(speciality__level__departement__est=est).distinct()
        elif model == Module:
            return model.objects.filter(specialityMod__level__departement__est=est).distinct()
        elif model == Department:
            return model.objects.filter(est=est).distinct()
        elif model == TargetedPublic:
            return model.objects.filter(id=est.id).distinct()
        elif model == Role:
            return model.objects.filter(departement__est=est).distinct()
        elif model == Space:
            return model.objects.filter(departements__est=est).distinct()
        elif model == TimeSlot:
            return model.objects.filter(departements__est=est).distinct()
        elif model == AdvancedUserProfile:
            return model.objects.filter(modules__specialityMod__level__departement__est=est,est=est).distinct()
        elif model == BasicUserProfile:
            return model.objects.filter(speciality__level__departement__est=est).distinct()
        elif model == Absence:
            return model.objects.filter(user__modules__specialityMod__level__departement__est=est).distinct()
        elif model == busyTimeSelect:
            return model.objects.filter(user__modules__specialityMod__level__departement__est=est).distinct()
        elif model == SpacePreference:
            return model.objects.filter(user__modules__specialityMod__level__departement__est=est).distinct()
        elif model == GroupPreference:
            return model.objects.filter(user__speciality__level__departement__est=est).distinct()
        elif model == EstablishmentAdminProfile:
            return model.objects.filter(est=est).distinct()
        elif model == DepartementAdminProfile:
            return model.objects.filter(departement__est=est).distinct()
        elif model == GroupPreference:
            return model.objects.filter(user__speciality__level__departement__est=est).distinct()
        elif model == User:
            return model.objects.filter(
                Q(Advanceduser_profile__est=request.user.estAdminProfile.est) |
                Q(estAdminProfile__est=request.user.estAdminProfile.est) |
                Q(depAdminProfile__departement__est=request.user.estAdminProfile.est) |
                Q(BasicUser_profile__speciality__level__departement__est=request.user.estAdminProfile.est)).distinct()
        return model.objects.filter(departement__est=est)

    if request.user.role == 'dep_admin':
        dep = request.user.depAdminProfile.departement
        if model == Speciality:
            return model.objects.filter(level__departement=dep).distinct()
        elif model.__name__ == 'Group':
            return model.objects.filter(speciality__level__departement=dep).distinct()
        elif model == Module:
            return model.objects.filter(specialityMod__level__departement=dep).distinct()
        elif model == Department:
            return model.objects.filter(id=dep.id).distinct()
        elif model == TargetedPublic:
            return model.objects.filter(id=dep.est.id).distinct()
        elif model == Space:
            return model.objects.filter(departements=dep).distinct()
        elif model == TimeSlot:
            return model.objects.filter(departements=dep).distinct()
        elif model == AdvancedUserProfile:
            return model.objects.filter(modules__specialityMod__level__departement=dep).distinct()
        elif model == BasicUserProfile:
            return model.objects.filter(speciality__level__departement=dep).distinct()
        elif model == DepartementAdminProfile:
            return model.objects.filter(departement=dep).distinct()
        elif model == Absence:
            return model.objects.filter(user__modules__specialityMod__level__departement=dep).distinct()
        elif model == busyTimeSelect:
            return model.objects.filter(user__modules__specialityMod__level__departement=dep).distinct()
        elif model == SpacePreference:
            return model.objects.filter(user__modules__specialityMod__level__departement=dep).distinct()
        elif model == GroupPreference:
            return model.objects.filter(user__speciality__level__departement=dep).distinct()
        elif model == Role:
            return model.objects.filter(departement=dep).distinct()
        elif model == User:
            return model.objects.filter(
                Q(Advanceduser_profile__modules__specialityMod__level__departement=dep) |
                Q(depAdminProfile__departement=dep) |
                Q(BasicUser_profile__speciality__level__departement=dep)).distinct()

        return model.objects.filter(departement=dep)

    if request.user.is_staff and request.user.role == 'advancedUser':
        dep = request.user.Advanceduser_profile.Role.departement
        if model == Speciality:
            return model.objects.filter(level__departement=dep).distinct()
        elif model.__name__ == 'Group':
            return model.objects.filter(speciality__level__departement=dep).distinct()
        elif model == Module:
            return model.objects.filter(specialityMod__level__departement=dep).distinct()
        elif model == Department:
            return model.objects.filter(id=dep.id).distinct()
        elif model == TargetedPublic:
            return model.objects.filter(id=dep.est.id).distinct()
        elif model == Space:
            return model.objects.filter(departements=dep).distinct()
        elif model == TimeSlot:
            return model.objects.filter(departements=dep).distinct()
        elif model == AdvancedUserProfile:
            return model.objects.filter(modules__specialityMod__level__departement=dep).distinct()
        elif model == BasicUserProfile:
            return model.objects.filter(speciality__level__departement=dep).distinct()
        elif model == Absence:
            return model.objects.filter(user__modules__specialityMod__level__departement=dep).distinct()
        elif model == busyTimeSelect:
            return model.objects.filter(user__modules__specialityMod__level__departement=dep).distinct()
        elif model == SpacePreference:
            return model.objects.filter(user__modules__specialityMod__level__departement=dep).distinct()
        elif model == GroupPreference:
            return model.objects.filter(user__speciality__level__departement=dep).distinct()
        elif model == Role:
            return model.objects.filter(departement=dep).distinct()
        elif model == User:
            return model.objects.filter(
                Q(Advanceduser_profile__modules__specialityMod__level__departement=dep) |
                Q(BasicUser_profile__speciality__level__departement=dep)).distinct()
        return model.objects.filter(departement=dep)

    return model.objects.none()


class CustomGroupAdmin(GroupAdmin):

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if 'permissions' in form.base_fields:
            widget = form.base_fields['permissions'].widget
            widget.attrs.update({
                'style': 'overflow-x: auto; white-space: nowrap; display: block; width: 100%; min-height: 300px;'
            })

        return form
    def has_module_permission(self, request): #lets the model show up in the admin sidebar
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):  #lets staff view the list and detail pages
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email')}),
        ('Rôles & Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
    )

    ordering = ('username',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.role == 'est_admin':
            return qs.filter(
                Q(Advanceduser_profile__modules__specialityMod__level__departement__est=request.user.estAdminProfile.est) |
                Q(estAdminProfile__est=request.user.estAdminProfile.est) |
                Q(depAdminProfile__departement__est=request.user.estAdminProfile.est) |
                Q(BasicUser_profile__speciality__level__departement__est=request.user.estAdminProfile.est)).distinct()
        if request.user.role == 'dep_admin':
            return qs.filter(
                Q(Advanceduser_profile__modules__specialityMod__level__departement=request.user.depAdminProfile.departement) |
                Q(depAdminProfile__departement=request.user.depAdminProfile.departement) |
                Q(BasicUser_profile__speciality__level__departement=request.user.depAdminProfile.departement)).distinct()
        if request.user.is_staff and request.user.role == 'advancedUser':
            return qs.filter(
                Q(Advanceduser_profile__modules__specialityMod__level__departement=request.user.Advanceduser_profile.Role.departement) |
                Q(BasicUser_profile__speciality__level__departement=request.user.Advanceduser_profile.Role.departement)).distinct()
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'is_superuser' in form.base_fields:
                form.base_fields['is_superuser'].disabled = True
            '''if 'groups' in form.base_fields:
                form.base_fields['groups'].queryset = request.user.groups.all()'''
            if request.user.role == 'est_admin':
                if 'role' in form.base_fields:
                    form.base_fields['role'].choices = [('advancedUser', 'Enseignant'), ('basicUser', 'Etudiant'),
                                                        ('dep_admin', 'Administrateur Département')]
            elif request.user.role == 'dep_admin':
                if 'role' in form.base_fields:
                    form.base_fields['role'].choices = [('advancedUser', 'Enseignant'), ('basicUser', 'Etudiant')]


        action_map = {
            "add": "Ajouter",
            "change": "Modifier",
            "delete": "Supprimer",
            "view": "Voir"
        }

        def permission_label(obj):
            action = obj.codename.split('_')[0]
            try:
                model_class = obj.content_type.model_class()
                model_name = model_class._meta.verbose_name.capitalize()
            except:
                # fallback if model is deleted or not found
                model_name = obj.content_type.model.capitalize()
            return f"{action_map.get(action, action.capitalize())} {model_name}"

        if 'user_permissions' in form.base_fields:  #add an horizental scroll bar to the autorisations field
            widget = form.base_fields['user_permissions'].widget
            widget.attrs.update({
                'style': 'overflow-x: auto; white-space: nowrap; display: block; width: 100%; min-height: 300px;'
            })
            group_ct = ContentType.objects.get(app_label='auth', model='group')
            form.base_fields['user_permissions'].queryset = form.base_fields['user_permissions'].queryset.exclude(
                content_type=group_ct)
            form.base_fields['user_permissions'].label_from_instance = permission_label

        return form

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.role in ['est_admin', 'dep_admin']


@admin.register(EstablishmentAdminProfile)
class EstablishmentAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('est', 'first_name', 'last_name', 'email')
    list_filter = ('est', 'first_name', 'last_name')
    search_fields = ('est__name', 'first_name', 'last_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.role == 'est_admin':
            return qs.filter(est=request.user.estAdminProfile.est)
        if request.user.role == 'dep_admin':
            return qs.filter(est=request.user.depAdminProfile.departement.est)
        if request.user.is_staff and request.user.role == 'advancedUser':
            return qs.filter(est=request.user.Advanceduser_profile.Role.departement.est)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser and request.user.role == 'est_admin':
            admin_est = request.user.estAdminProfile.est
            if 'est' in form.base_fields:
                form.base_fields['est'].queryset = get_filtered_queryset(request, TargetedPublic)
                form.base_fields['est'].initial = admin_est
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, User)
        return form

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and request.user.role == 'est_admin' and not change:
            obj.est = request.user.estAdminProfile.est
        super().save_model(request, obj, form, change)


@admin.register(DepartementAdminProfile)
class DepartementAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('departement', 'first_name', 'last_name', 'email')
    list_filter = ('departement', 'first_name', 'last_name')
    search_fields = ('departement__name', 'first_name', 'last_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.role == 'est_admin':
            return qs.filter(departement__est=request.user.estAdminProfile.est)
        if request.user.role == 'dep_admin':
            return qs.filter(departement=request.user.depAdminProfile.departement)
        if request.user.is_staff and request.user.role == 'advancedUser':
            departements = Department.objects.filter(
                id__in=request.user.Advanceduser_profile.modules.values_list('specialityMod__level__departement__id',
                                                    flat=True),est=request.user.Advanceduser_profile.est).distinct()
            return qs.filter(departement__in=departements)
        return qs.none()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'departement' in form.base_fields:
                form.base_fields['departement'].queryset = get_filtered_queryset(request, Department)
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, User)
        return form


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'departement')
    list_filter = ('name', 'departement')
    search_fields = ('name', 'departement')

    def get_queryset(self, request):
        return get_filtered_queryset(request, Role)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'departement' in form.base_fields:
                form.base_fields['departement'].queryset = get_filtered_queryset(request, Department)
        return form


@admin.register(AdvancedUserProfile)
class AdvancedUserProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'matricule', 'grade', 'Liste_modules')
    list_filter = ('grade','Role')
    search_fields = ('first_name', 'last_name', 'matricule', 'grade__name')

    def Liste_modules(self, obj):
        return ", ".join([m.module_name for m in obj.modules.all()])

    def get_queryset(self, request):
        return get_filtered_queryset(request, AdvancedUserProfile)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, User)
            if 'est' in form.base_fields:
                form.base_fields['est'].queryset = get_filtered_queryset(request, TargetedPublic)
            if 'modules' in form.base_fields:
                form.base_fields['modules'].queryset = get_filtered_queryset(request, Module)
            if 'Role' in form.base_fields:
                form.base_fields['Role'].queryset = get_filtered_queryset(request, Role)
        return form

    change_list_template = "Admin/changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel),
            path('download-template/', self.download_template),
        ]
        return my_urls + urls

    def download_template(self, request):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Template"

            headers = [
                "Nom", "Prénom", "Matricule", "Grade",
                "Role", "Date de naissance", "Téléphone",
                "Email", "Adresse"
            ]
            ws.append(headers)

            grades = Grade.objects.all().values_list('name',flat=True)
            roles = get_filtered_queryset(request, Role).values_list('name', flat=True)

            def add_dropdown(column, choices):
                dv = DataValidation(type="list", formula1=f'"{",".join(choices)}"')
                ws.add_data_validation(dv)
                dv.add(f'{column}2:{column}1048576')

            add_dropdown('D', grades)  # Grade
            add_dropdown('E', roles)  # Role

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=Enseignant.xlsx'
            wb.save(response)
            return response
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return HttpResponse("Error while generating Excel", status=500)

    def import_excel(self, request):
        try:
            if request.method == "POST":
                form = ExcelImportForm(request.POST, request.FILES)
                if form.is_valid():
                    verbose_to_field = {
                        'Nom': 'first_name',
                        'Prénom': 'last_name',
                        'Matricule': 'matricule',
                        "Grade": "grade",
                        "Role": "Role",
                        "Date de naissance": "birth_date",
                        "Téléphone": "phone_number",
                        "Email": "email",
                        "Adresse": "address",
                    }

                    if request.user.role == 'est_admin':
                        user_est=request.user.estAdminProfile.est
                    elif request.user.role == 'dep_admin':
                        user_est=request.user.depAdminProfile.departement.est
                    elif request.user.is_staff and request.user.role == 'advancedUser':
                        user_est=request.user.Advanceduser_profile.est
                    else:
                        user_est = TargetedPublic.objects.filter(id=1).first()

                    try:
                        excel_file = request.FILES['excel_file']
                        #df = pd.read_excel(request.FILES['excel_file'])
                        df = pd.read_excel(excel_file, engine='openpyxl')  # Explicit engine

                        df.rename(columns=verbose_to_field, inplace=True)

                        count = 0
                        for _, row in df.iterrows():
                            for each in verbose_to_field.values():
                                if pd.isna(row[each]):
                                    row[each] = None
                            if not AdvancedUserProfile.objects.filter(matricule=row['matricule']).exists():
                                role_obj = get_filtered_queryset(request, Role).get(name=row['Role']) if row['Role'] else None
                                grade_obj = get_filtered_queryset(request, Grade).get(name=row['grade']) if row['grade'] else None
                                clean_est_name = re.sub(r'\W+', '', user_est.name.lower())
                                username = f"{clean_est_name}_{row['matricule'][-4:]}"
                                aduser = AdvancedUserProfile.objects.create(
                                    est=user_est,
                                    first_name=row['first_name'],
                                    last_name=row['last_name'],
                                    matricule=row['matricule'],
                                    grade=grade_obj,
                                    Role=role_obj,
                                    birth_date=row['birth_date'],
                                    phone_number=row['phone_number'],
                                    email=row['email'],
                                    address=row['address'],
                                )

                                if not User.objects.filter(username=username).exists():
                                    user = User.objects.create(
                                        username=username,
                                        first_name=row['first_name'],
                                        last_name=row['last_name'],
                                        role="advancedUser")
                                    password = row['birth_date'].strftime('%d%m%Y') if not pd.isna(row['birth_date']) else "pass"
                                    user.set_password(password)
                                    user.save()
                                    aduser.user = user
                                else:
                                    aduser.user = User.objects.get(username=username)
                                aduser.save()
                                count += 1

                        if count > 0:
                            self.message_user(request, f"✅ {count} lignes importées avec succès!")
                        return redirect("..")
                    except Exception as e:
                        self.message_user(request, f"Erreur: {str(e)}", level='error')
                        return redirect("..")

            form = ExcelImportForm()
            return render(request, "Admin/excel_form.html", {
                "form": form,
                "has_download_template": True
            })

        except Exception as e:
            print("Unexpected error:", str(e))
            self.message_user(request, "An unexpected error occurred", level='error')
            return redirect("..")


@admin.register(BasicUserProfile)
class BasicUserProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'matricule', 'speciality', 'group')
    list_filter = ('first_name', 'last_name', 'matricule', 'speciality', 'group')
    search_fields = ('first_name', 'last_name', 'matricule', 'speciality__name', 'group__group_number')

    def get_queryset(self, request):
        return get_filtered_queryset(request, BasicUserProfile)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, User)
            if 'speciality' in form.base_fields:
                form.base_fields['speciality'].queryset = get_filtered_queryset(request, Speciality)
            if 'group' in form.base_fields:
                form.base_fields['group'].queryset = get_filtered_queryset(request, EducationalEstablishmentResources.models.Group)
        return form

    change_list_template = "Admin/changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-excel/', self.import_excel),
            path('download-template/', self.download_template),
        ]
        return my_urls + urls

    def download_template(self, request):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Template"

            headers = [
                "Nom", "Prénom", "Matricule", "Spécialité",
                "Groupe", "Date de naissance", "Téléphone",
                "Email", "Adresse", "Statut"
            ]
            ws.append(headers)

            specialities = get_filtered_queryset(request, Speciality).values_list('name', flat=True)
            groups = get_filtered_queryset(request, EducationalEstablishmentResources.models.Group).values_list(
                'group_number', flat=True)
            groups_choices=[str(group) for group in groups]
            status_choices = ['Actif', 'Diplômé', 'Exclu']

            def add_dropdown(column, choices):
                dv = DataValidation(type="list", formula1=f'"{",".join(choices)}"')
                ws.add_data_validation(dv)
                dv.add(f'{column}2:{column}1048576')

            add_dropdown('D', specialities)  # Spécialité
            add_dropdown('E', groups_choices)  # Groupe
            add_dropdown('J', status_choices)  # Statut

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=Etudiants.xlsx'
            wb.save(response)
            return response
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return HttpResponse("Error while generating Excel", status=500)

    def import_excel(self, request):
        try:
            if request.method == "POST":
                form = ExcelImportForm(request.POST, request.FILES)
                if form.is_valid():
                    verbose_to_field = {
                        'Nom': 'first_name',
                        'Prénom': 'last_name',
                        'Matricule': 'matricule',
                        "Spécialité": "speciality",
                        "Groupe": "group",
                        "Date de naissance": "birth_date",
                        "Téléphone": "phone_number",
                        "Email": "email",
                        "Adresse": "address",
                        "Statut": "status",
                    }

                    try:
                        excel_file = request.FILES['excel_file']
                        #df = pd.read_excel(request.FILES['excel_file'])
                        df = pd.read_excel(excel_file, engine='openpyxl')  # Explicit engine

                        df.rename(columns=verbose_to_field, inplace=True)

                        count = 0
                        for _, row in df.iterrows():

                            for each in verbose_to_field.values():
                                if pd.isna(row[each]):
                                    row[each] = None

                            statut_map = {
                                'Actif': 'Active',
                                'Diplômé': 'Graduated',
                                'Exclu': 'Expelled',
                            }
                            statut_value = statut_map.get(row['status'])
                            if statut_value is None:
                                raise ValueError(f"Statut invalide: {row['status']}")



                            speciality_obj = get_filtered_queryset(request, Speciality).get(name=row['speciality']) if row['speciality'] else None
                            if pd.notna(row['group']) and str(row['group']).strip() != "":
                                group_obj = get_filtered_queryset(request, EducationalEstablishmentResources.models.Group
                                ).filter(speciality=speciality_obj, group_number=row['group']).first()

                                if not group_obj:
                                    raise ValueError(
                                        f"Groupe {row['group']} non trouvé pour la spécialité {row['speciality']}")
                            else:
                                group_obj = None  # No group assigned
                            if not BasicUserProfile.objects.filter(matricule=row['matricule']).exists():
                                buser = BasicUserProfile.objects.create(
                                    first_name=row['first_name'],
                                    last_name=row['last_name'],
                                    matricule=row['matricule'],
                                    speciality=speciality_obj,
                                    group=group_obj,
                                    birth_date=row['birth_date'],
                                    phone_number=row['phone_number'],
                                    email=row['email'],
                                    address=row['address'],
                                    status=statut_value,
                                )

                                if not User.objects.filter(username=row['matricule']).exists():
                                    user = User.objects.create(
                                        username=row['matricule'],
                                        first_name=row['first_name'],
                                        last_name=row['last_name'],
                                        role="basicUser")
                                    password = row['birth_date'].strftime('%d%m%Y') if not pd.isna(row['birth_date']) else "pass"
                                    user.set_password(password)
                                    user.save()
                                    buser.user = user
                                else:
                                    buser.user = User.objects.get(username=row['matricule'])
                                buser.save()
                                count += 1

                        if count > 0:
                            self.message_user(request, f"✅ {count} lignes importées avec succès!")
                        return redirect("..")
                    except Exception as e:
                        self.message_user(request, f"Erreur: {str(e)}", level='error')
                        return redirect("..")

            form = ExcelImportForm()
            return render(request, "Admin/excel_form.html", {
                "form": form,
                "has_download_template": True
            })

        except Exception as e:
            self.message_user(request, "An unexpected error occurred", level='error')
            return redirect("..")


@admin.register(GroupPreference)
class GroupPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'chosenGroup', 'updated_at')
    list_filter = ('user', 'chosenGroup', 'updated_at')
    search_fields = ('user__matricule', 'chosenGroup__group_number', 'updated_at')

    def get_queryset(self, request):
        return get_filtered_queryset(request, GroupPreference)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, BasicUserProfile)
            if 'chosenGroup' in form.base_fields:
                form.base_fields['chosenGroup'].queryset = get_filtered_queryset(request, EducationalEstablishmentResources.models.Group)
        return form


@admin.register(SpacePreference)
class SpacePreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'chosenSpace', 'day', 'time', 'is_approved')
    list_filter = ('user', 'chosenSpace', 'day', 'time')
    search_fields = ('user__matricule', 'chosenSpace__group_number', 'day__name', 'time__start_time')

    def get_queryset(self, request):
        return get_filtered_queryset(request, SpacePreference)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, AdvancedUserProfile)
            if 'chosenSpace' in form.base_fields:
                form.base_fields['chosenSpace'].queryset = get_filtered_queryset(request, Space)
            if 'chosenModule' in form.base_fields:
                form.base_fields['chosenModule'].queryset = get_filtered_queryset(request, Module)
            if 'time' in form.base_fields:
                form.base_fields['time'].queryset = get_filtered_queryset(request, TimeSlot)
        return form


@admin.register(busyTimeSelect)
class BusyTimeAdmin(admin.ModelAdmin):
    list_display = ('user', 'busyday', 'is_approved')
    list_filter = ('user', 'busyday')
    search_fields = ('user__matricule', 'busyday__name')

    def get_queryset(self, request):
        return get_filtered_queryset(request, busyTimeSelect)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, AdvancedUserProfile)
            if 'busytime' in form.base_fields:
                form.base_fields['busytime'].queryset = get_filtered_queryset(request, TimeSlot)
        return form


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_absent', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__matricule',)
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        return get_filtered_queryset(request, Absence)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if 'user' in form.base_fields:
                form.base_fields['user'].queryset = get_filtered_queryset(request, AdvancedUserProfile)
            if 'absent_times' in form.base_fields:
                form.base_fields['absent_times'].queryset = get_filtered_queryset(request, TimeSlot)
        return form