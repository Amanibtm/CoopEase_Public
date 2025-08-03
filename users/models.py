from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.hashers import make_password
from CoopEaseAll import settings
from EducationalEstablishmentResources.models import Speciality, Group, Module
from sharedResources.models import Department, Day, TimeSlot, Space, TargetedPublic, Grade
from django.utils import timezone
import re


class User(AbstractUser):
    ROLE_CHOICES = [
        ('basicUser', 'Etudiant'),
        ('advancedUser', 'Enseignant'),
        ('est_admin', 'Administrateur Établissement'),
        ('dep_admin', 'Administrateur Département'),
        ('superuser','SuperUser')
    ]
    role = models.CharField("Rôle", max_length=12, choices=ROLE_CHOICES)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_groups",
        blank=True,
        verbose_name="Groupes"
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_permissions",
        blank=True,
        verbose_name="Autorisations"
    )

    def __str__(self):
        return f"{self.username} - {self.first_name}"

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def save(self, *args, **kwargs):
        # Hash password only if it's not already hashed
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


class Role(models.Model):
    departement = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="Role_departement", verbose_name="Département")
    name = models.CharField("Nom", max_length=20,choices=[('Responsable','Responsable')],default='Responsable')


    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        constraints = [
            models.UniqueConstraint(fields=['departement', 'name'], name="unique_role_per_departement")
        ]


    def __str__(self):
        return self.name


class AdvancedUserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="Advanceduser_profile", null=True, blank=True, verbose_name="Compte utilisateur")
    est = models.ForeignKey(TargetedPublic, on_delete=models.CASCADE,default=1)
    first_name = models.CharField("Nom", max_length=20, default='Utilisateur')
    last_name = models.CharField("Prénom", max_length=20, default='Enseignant')
    matricule = models.CharField("Matricule", max_length=20)
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Grade")
    Role = models.ForeignKey(Role, on_delete=models.SET_NULL, related_name="enseignants", null=True, blank=True)
    modules = models.ManyToManyField(Module, blank=True, verbose_name="Modules")
    birth_date = models.DateField("Date de naissance", null=True, blank=True)
    phone_number = models.CharField("Téléphone", max_length=13, blank=True)
    email = models.EmailField("Email", max_length=254, blank=True, null=True)
    address = models.TextField("Adresse", blank=True, null=True)
    photo = models.ImageField("Photo", upload_to='advancedUsers_photos/', blank=True, null=True)

    class Meta:
        verbose_name = "Enseignant"
        verbose_name_plural = "Enseignants"
        constraints = [
            models.UniqueConstraint(fields=['est', 'matricule'], name="unique_enseignant")
        ]

    def __str__(self):
        return f"{self.first_name} - {self.matricule}"

    def save(self, *args, **kwargs):
        # Capitalize only the first letter of each name
        self.first_name = str(self.first_name).title() if self.first_name else ''
        self.last_name = str(self.last_name).title() if self.last_name else ''

        clean_est_name = re.sub(r'\W+', '', self.est.name.lower())
        username=f"{clean_est_name}_{self.matricule[-4:]}"
        #automatically create user account if it doesn't exist
        if not User.objects.filter(username=username).exists():
            user = User.objects.create(
                username=username,
                first_name=self.first_name,
                last_name=self.last_name,
                role="advancedUser",
            )
            password = self.birth_date.strftime('%d%m%Y') if self.birth_date else "pass"
            user.set_password(password)#user.set_password(str(self.birth_date))
            user.save()
            self.user = user     #Link the user to this advancedUserProfile
        super().save(*args, **kwargs)



class BasicUserProfile(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Actif'), ('Graduated', 'Diplômé'), ('Expelled', 'Exclu'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="BasicUser_profile", null=True, blank=True, verbose_name="Compte utilisateur")
    first_name = models.CharField("Prénom", max_length=20, default='Basic')
    last_name = models.CharField("Nom", max_length=20, default='User')
    matricule = models.CharField("Matricule", max_length=20, unique=True)
    speciality = models.ForeignKey(Speciality, on_delete=models.PROTECT, related_name="spc_BasicUser", blank=True,null=True, verbose_name="Spécialité")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Groupe")
    academic_year = models.IntegerField("Année académique", blank=True, null=True)
    birth_date = models.DateField("Date de naissance", blank=True, null=True)
    phone_number = models.CharField("Téléphone", max_length=13, blank=True, null=True)
    email = models.EmailField("Email", max_length=254, blank=True, null=True)
    address = models.TextField("Adresse", blank=True, null=True)
    status = models.CharField("Statut", max_length=10, choices=STATUS_CHOICES, default='Active', null=True, blank=True)
    photo = models.ImageField("Photo", upload_to='BasicUsers_photos/', blank=True, null=True)

    class Meta:
        verbose_name = "Etudiant"
        verbose_name_plural = "Etudiants"

    def __str__(self):
        return f"{self.first_name} - {self.matricule}"

    def save(self, *args, **kwargs):
        # Capitalize only the first letter of each name
        self.first_name = str(self.first_name).title() if self.first_name else ''
        self.last_name = str(self.last_name).title() if self.last_name else ''

        # ✅ Automatically create User if it doesn't exist
        if not User.objects.filter(username=self.matricule).exists():
            user = User.objects.create(
                username=self.matricule,  # Matricule as username
                first_name=self.first_name,
                last_name=self.last_name,
                role="basicUser")
            password = self.birth_date.strftime('%d%m%Y') if self.birth_date else "pass"
            user.set_password(password)
            user.save()
            self.user = user  # Link the user to this BasicUserProfile

        super().save(*args, **kwargs)



class EstablishmentAdminProfile(models.Model):
    est = models.ForeignKey(TargetedPublic, on_delete=models.CASCADE, related_name='estadmins', verbose_name="Établissement")
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, related_name="estAdminProfile", verbose_name="Utilisateur")
    first_name = models.CharField("Nom", max_length=50)
    last_name = models.CharField("Prénom", max_length=50)
    birth_date = models.DateField("Date de naissance", blank=True, null=True)
    email = models.EmailField(blank=True,null=True)
    phone = models.CharField("Numéro de téléphone", max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Admin de l'etablissement"
        verbose_name_plural = "Admins des etablissements"

    def __str__(self):
        return f"Admin de {self.est}"

    def save(self, *args, **kwargs):
        self.first_name = str(self.first_name).title()
        self.last_name = str(self.last_name).title()

        if not self.user:
            user = User.objects.create(
                username=self.est.name.lower().replace(" ", "_") + "_admin",
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email,
                role='est_admin',
                is_staff=True  #allow login to admin panel
                )
            password = self.birth_date.strftime('%d%m%Y') if self.birth_date else "pass"
            user.set_password(password)
            user.save()
            self.user = user

        super().save(*args, **kwargs)


class DepartementAdminProfile(models.Model):
    departement = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='depadmins', verbose_name="Département")
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True, related_name="depAdminProfile", verbose_name="Utilisateur")
    first_name = models.CharField("Nom", max_length=50)
    last_name = models.CharField("Prénom", max_length=50)
    birth_date = models.DateField("Date de naissance", blank=True, null=True)
    email = models.EmailField("Email",blank=True,null=True)
    phone = models.CharField("Numéro de téléphone", max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Admin du département"
        verbose_name_plural = "Admins des départements"
        constraints = [
            models.UniqueConstraint(fields=['departement', 'user'], name="unique_admin_dep")
        ]

    def __str__(self):
        return f"Admin de {self.departement.name}"

    def save(self, *args, **kwargs):
        self.first_name = str(self.first_name).title()
        self.last_name = str(self.last_name).title()

        if not self.user:
            user = User.objects.create(
                username=self.departement.name.lower().replace(" ", "_") + "_admin",
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email,
                role='dep_admin',
                is_staff=True  #allow login to admin panel
                )
            password = self.birth_date.strftime('%d%m%Y') if self.birth_date else "pass"
            user.set_password(password)
            user.save()
            self.user = user

        super().save(*args, **kwargs)



class GroupPreference(models.Model):
    user = models.OneToOneField(BasicUserProfile, on_delete=models.CASCADE, related_name="grp_prf", null=True, blank=True, verbose_name="Utilisateur")
    chosenGroup = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="grp_chosen", null=True, blank=True, verbose_name="Groupe choisi")
    updated_at = models.DateTimeField("Dernière modification", auto_now=True)

    class Meta:
        verbose_name = "Groupe Choisi"
        verbose_name_plural = "Groupes Choisis"

    def __str__(self):
        return f"{self.user} - Groupe {self.chosenGroup}"


class SpacePreference(models.Model):
    user = models.ForeignKey(AdvancedUserProfile, on_delete=models.CASCADE, related_name="space", verbose_name="Utilisateur")
    chosenSpace = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="space_chosen", verbose_name="Salle")
    chosenModule = models.ForeignKey(Module, on_delete=models.CASCADE, verbose_name="Module", null=True, blank=True)
    day = models.ForeignKey(Day, on_delete=models.CASCADE, related_name="day", null=True, blank=True, verbose_name="Jour")
    time = models.ForeignKey(TimeSlot, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Heure")
    Modtype = models.CharField("Type Module", max_length=50, null=True, blank=True)
    group = models.CharField("Groupe", max_length=50, null=True, blank=True)
    section = models.CharField("Section", max_length=50, null=True, blank=True)
    reservation_date = models.DateField(default=timezone.now,null=True,blank=True, verbose_name="Date de Réservation")
    timestamp = models.DateTimeField(auto_now_add=True,verbose_name="Date d'opération")  #This will store the creation time
    is_approved = models.BooleanField("Approuvé", default=False)  # New field

    class Meta:
        verbose_name = "Reservation de salle"
        verbose_name_plural = "Les reservations des salles"
        constraints = [
            models.UniqueConstraint(fields=['chosenSpace', 'day', 'time', 'reservation_date'], name="unique_room_per_type")
        ]

    def __str__(self):
        return f"{self.user} - {self.chosenSpace} - {self.day} - {self.time} - {self.reservation_date}"

class busyTimeSelect(models.Model):
    user = models.ForeignKey(AdvancedUserProfile, on_delete=models.CASCADE, related_name="bt", null=True, blank=True, verbose_name="Utilisateur")
    busyday = models.ForeignKey(Day, on_delete=models.CASCADE, related_name="busyday", verbose_name="Jour d’indisponibilité")
    busytime = models.ManyToManyField(TimeSlot, related_name="busytime", verbose_name="Créneaux indisponibles")
    timestamp = models.DateTimeField(auto_now_add=True,verbose_name="Date d'opération")  # <--- This will store the creation time
    is_approved = models.BooleanField("Approuvé", default=False)  # New field


    class Meta:
        verbose_name = "Indisponibilité"
        verbose_name_plural = "Indisponibilités"

    def __str__(self):
        return f"{self.user} _ {self.busyday.name}"


class Absence(models.Model):
    user = models.ForeignKey(AdvancedUserProfile, on_delete=models.CASCADE, related_name="absence_record", null=True, blank=True, verbose_name="Utilisateur")
    is_absent = models.BooleanField("Absent", default=True, help_text="L'utilisateur est-il absent ?")
    created_at = models.DateTimeField("Date d'enregistrement", auto_now_add=True)
    date = models.DateField(default=timezone.now, verbose_name="Date d'absence")
    absent_times = models.ManyToManyField(TimeSlot, related_name="absent_times", verbose_name="Heures d'absence")
    timestamp = models.DateTimeField(auto_now_add=True)  # <--- This will store the creation time

    class Meta:
        verbose_name = "Absence"
        verbose_name_plural = "Absences"
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name="unique_absence_time")
        ]

    def __str__(self):
        return f"Absence de {self.user} - {self.created_at.strftime('%Y-%m-%d')}"


