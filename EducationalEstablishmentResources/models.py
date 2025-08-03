from django.core.validators import MinValueValidator, MaxValueValidator
from sharedResources.models import *
from django.core.exceptions import ValidationError

class Level(models.Model):
    """Niveaux d'étude : Licence 1, Master 2, etc."""
    departement = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="dept",null=True,blank=True, verbose_name="Département")
    name = models.CharField("Nom du niveau", max_length=50)

    class Meta:
        verbose_name = "Niveau d'étude"
        verbose_name_plural = "Niveaux d'étude"
        constraints = [
            models.UniqueConstraint(fields=['departement', 'name'], name='unique_level')
        ]

    def __str__(self):
        return f"{self.name} - {self.departement}"


class Speciality(models.Model):
    """Spécialités disponibles (ex: Informatique, Mathématiques)"""
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="specialities", verbose_name="Niveau")
    name = models.CharField("Acronyme de la spécialité", max_length=50)
    speciality_nom_complet = models.CharField("Nom du specialité", max_length=100, null=True, blank=True)
    sections = models.IntegerField("Nombre de sections",default=1)
    is_activated = models.BooleanField("Activé", default=True)  # New field

    class Meta:
        verbose_name = "Spécialité"
        verbose_name_plural = "Spécialités"
        constraints = [
            models.UniqueConstraint(fields=['level', 'name'], name='unique_speciality')
        ]


    def __str__(self):
        return f"{self.name} - {self.level.name}"


class Group(models.Model):
    """Groupes d'étudiants au sein d'une spécialité"""
    speciality = models.ForeignKey(Speciality, on_delete=models.CASCADE, related_name="groups", verbose_name="Spécialité")
    group_number = models.IntegerField("Numéro du groupe", validators=[MinValueValidator(1), MaxValueValidator(50)])
    section = models.IntegerField(blank=True, null=True)
    capacity = models.IntegerField("Nombre des étudiants", default=25, blank=True, null=True)

    class Meta:
        verbose_name = "Groupe"
        verbose_name_plural = "Groupes"
        constraints = [
            models.UniqueConstraint(fields=['speciality', 'group_number'], name='unique_spc_group')
        ]

    def __str__(self):
        return f"{self.speciality} - Groupe {self.group_number}"


class Module(models.Model):
    specialityMod = models.ForeignKey(Speciality, on_delete=models.CASCADE, related_name='modules', verbose_name="Spécialité")
    module_name = models.CharField(max_length=50, verbose_name='Acronyme du module')
    module_nom_complet = models.CharField("Nom du module", max_length=100, null=True, blank=True)
    coefficient = models.IntegerField("Coefficient", validators=[MinValueValidator(0), MaxValueValidator(30)], null=True, blank=True)
    credit = models.IntegerField("Crédit", validators=[MinValueValidator(1), MaxValueValidator(30)], null=True, blank=True)
    TD = models.ForeignKey(typeSalle, on_delete=models.SET_NULL, blank=True, null=True, related_name='TD', verbose_name="TD ? Type salle")
    TP = models.ForeignKey(typeSalle, on_delete=models.SET_NULL, blank=True, null=True, related_name='TP',verbose_name="TP ? Type salle")
    Cours = models.ForeignKey(typeSalle, on_delete=models.SET_NULL, blank=True, null=True, related_name='Cours',verbose_name="Cours ? Type salle")
    nbrTDSemaine = models.IntegerField("Nombre TD par Semaine", default=0, validators=[MinValueValidator(0), MaxValueValidator(40)])
    nbrTPSemaine = models.IntegerField("Nombre TP par Semaine",default=0, validators=[MinValueValidator(0), MaxValueValidator(40)])
    nbrCoursSemaine = models.IntegerField("Nombre Cours par Semaine",default=0, validators=[MinValueValidator(0), MaxValueValidator(40)])
    examTimeslots = models.IntegerField("Nombre d'unités de temps d'examen",default=0, validators=[MinValueValidator(0), MaxValueValidator(40)])
    mode_evaluation = models.CharField("Mode d'évaluation", max_length=50, choices=[
        ('Continu', 'Contrôle continu'),
        ('Examen', 'Examen final'),
        ('Both', 'Contrôle continu + Examen final'),
    ])
    semester = models.CharField("Semestre", max_length=50, choices=[
        ('s1', 'Semestre 1'),
        ('s2', 'Semestre 2')
    ], blank=True, null=True)

    is_activated = models.BooleanField("Activé", default=True)  # New field


    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        constraints = [
            models.UniqueConstraint(fields=['module_name', 'specialityMod'], name='unique_module_per_spec')
        ]

    def __str__(self):
        return f"{self.module_name} - {self.specialityMod}"


    def clean(self):
        errors = {}

        if self.TD is not None and (self.nbrTDSemaine is None or self.nbrTDSemaine < 1):
            errors['nbrTDSemaine'] = "Si le champ TD est renseigné, le nombre de TD par semaine doit être au moins 1."

        if self.TP is not None and (self.nbrTPSemaine is None or self.nbrTPSemaine < 1):
            errors['nbrTPSemaine'] = "Si le champ TP est renseigné, le nombre de TP par semaine doit être au moins 1."

        if self.Cours is not None and (self.nbrCoursSemaine is None or self.nbrCoursSemaine < 1):
            errors['nbrCoursSemaine'] = "Si le champ Cours est renseigné, le nombre de Cours par semaine doit être au moins 1."

        if errors:
            raise ValidationError(errors)



class Schedule(models.Model):
    speciality = models.ForeignKey(Speciality, on_delete=models.CASCADE, verbose_name="Spécialité")
    group = models.CharField("Groupe", max_length=50)  # "All" or number
    module = models.ForeignKey(Module, on_delete=models.CASCADE, verbose_name="Module")
    typeModule = models.CharField("Type de Module",max_length=50, null=True, blank=True)
    section = models.CharField("Section",max_length=50, null=True, blank=True)
    professor = models.ForeignKey('users.AdvancedUserProfile', on_delete=models.CASCADE, verbose_name="Enseignant")
    room_type = models.CharField("Type de salle", max_length=50)  # "TD", "TP", "Amphi"
    room_number = models.CharField("Numéro de salle", max_length=50)
    day = models.CharField("Jour", max_length=50)
    time = models.CharField("Heure", max_length=50)  # "08:00", etc
    school_year = models.CharField('Année Académique',max_length=50, default="2024/2025")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="heure d'enregistrement")
    is_activated = models.BooleanField("Activé", default=True)
    semester = models.CharField("Semestre", max_length=50, choices=[
        ('s1', 'Semestre 1'),
        ('s2', 'Semestre 2')
    ], blank=True, null=True)


    class Meta:
        verbose_name = "Emploi du temps"
        verbose_name_plural = "Emplois du temps"
        '''constraints = [
            models.UniqueConstraint(fields=['room_number', 'room_type', 'day', 'time', 'is_activated'], name='unique_room_booking')
        ]'''


    def __str__(self):
        return f"{self.speciality} - Sec{self.section}/G:{self.group} - {self.room_type}{self.room_number} | {self.module} @ {self.day} {self.time}"
