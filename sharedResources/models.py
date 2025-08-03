import re
from django.core.exceptions import ValidationError
from django.db import models

class typeEtablissement(models.Model):
    name=models.CharField("Nom", max_length=100, unique=True)
    class Meta:
        verbose_name = "Type d'Établissement"
        verbose_name_plural = "Types des Établissements"

    def __str__(self):
        return self.name

class TargetedPublic(models.Model):
    name = models.CharField("Nom", max_length=100, unique=True)
    type = models.ForeignKey(typeEtablissement,on_delete=models.SET_NULL,null=True,blank=True,verbose_name="Type")
    address = models.CharField("Adresse", max_length=100)
    SystemeEtudeEnGroupe=models.CharField("Système d'étude en groupe", choices=[('Groupe-Groupe','Groupe-Groupe'),('Groupes-Tous','Groupes-Tous')])
    systemSemestre=models.BooleanField("Système des semestre",default=False)
    debutsemestre=models.DateField("Début du semestre 1",null=True,blank=True)
    finsemestre=models.DateField("Début du semestre 2",null=True,blank=True)

    class Meta:
        verbose_name = "Établissement"
        verbose_name_plural = "Établissements"

    def __str__(self):
        return f'{self.name} - {self.address}'


    def clean(self):
        super().clean()

        if self.systemSemestre:
            if not self.debutsemestre or not self.finsemestre:
                raise ValidationError("Les dates de semestre sont requises.")
            if self.finsemestre <= self.debutsemestre:
                raise ValidationError("La date de fin du semestre doit être postérieure à la date de début.")
        else:
            if self.debutsemestre or self.finsemestre:
                raise ValidationError("Pour définir les dates de début des semestres, vous devez d’abord activer le système des semestres.")
            else:
                self.debutsemestre = None
                self.finsemestre = None


class Faculty(models.Model):
    est = models.ForeignKey(TargetedPublic, on_delete=models.PROTECT, related_name='faculties', verbose_name="Établissement")
    name = models.CharField("Nom de faculté", max_length=100, unique=True)


    class Meta:
        verbose_name = "faculté"
        verbose_name_plural = "facultés"

    def __str__(self):
        return f"{self.name} - {self.est}"


class Department(models.Model):
    est = models.ForeignKey(TargetedPublic, on_delete=models.SET_NULL, null=True, related_name='department', verbose_name="Établissement")
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, related_name='faculty', verbose_name="Faculté")
    name = models.CharField("Nom du département", max_length=100, unique=True)
    groupsCapacity = models.IntegerField("taille de groupe optimale", blank=True, null=True)


    class Meta:
        verbose_name = "Département"
        verbose_name_plural = "Départements"

    def __str__(self):
        return self.name



class Equipement(models.Model):
    departement = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="eqp_dept_Sec", verbose_name="Département")
    type = models.CharField("Type", max_length=100)
    Nserie = models.CharField("Numéro de série", unique=True)
    Matricule = models.CharField("Matricule", max_length=100, blank=True, null=True)
    Brand = models.CharField("Marque", max_length=100, blank=True, null=True)
    Status = models.CharField("État", default='New', max_length=100, choices=[('Fonctionnel','Fonctionnel'), ('En panne','En panne'), ('En réparation','En réparation'), ('Hors service','Hors service')])

    class Meta:
        verbose_name = "Équipement"
        verbose_name_plural = "Équipements"

    def __str__(self):
        return f'{self.type} ({self.Brand})'


class Day(models.Model):
    name = models.CharField("Nom du jour", max_length=10, unique=True)

    class Meta:
        verbose_name = "Jour"
        verbose_name_plural = "Jours"

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    departements = models.ManyToManyField(Department, blank=True,related_name="time_depts", verbose_name="Départements")
    day = models.ManyToManyField(Day, verbose_name="Jours")
    start_time = models.TimeField("Heure de début")
    end_time = models.TimeField("Heure de fin")

    class Meta:
        verbose_name = "Créneau horaire"
        verbose_name_plural = "Créneaux horaires"
        constraints = [
            models.UniqueConstraint(fields=['start_time', 'end_time'], name="unique_time_slot")
        ]

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"

class typeSalle(models.Model):
    name = models.CharField("Type de salle", max_length=50, unique=True)
    description = models.CharField("Déscription", max_length=500,blank=True,null=True)

    class Meta:
        verbose_name = "Type de salle"
        verbose_name_plural = "Types des salles"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        # Normalize the name by removing non-alphanumeric characters and converting to lowercase
        normalized_name = re.sub(r'[^a-zA-Z0-9]', '', self.name).lower()

        # Check against existing entries
        for existing in typeSalle.objects.exclude(pk=self.pk):
            existing_normalized = re.sub(r'[^a-zA-Z0-9]', '', existing.name).lower()
            if (normalized_name == existing_normalized) or (existing_normalized in normalized_name):
                raise ValidationError(
                    f"Un type de salle similaire existe déjà: {existing.name}. "
                )


    def save(self, *args, **kwargs):
        self.full_clean()  # This will call clean() method
        super().save(*args, **kwargs)


class Space(models.Model):
    departements = models.ManyToManyField(Department, blank=True,related_name="Spacesdept", verbose_name="Départements")
    room_number = models.CharField("Réf", max_length=10)
    capacity = models.IntegerField("Capacité", blank=True, null=True)
    room_type = models.ForeignKey(typeSalle, on_delete=models.SET_NULL, blank=True, null=True, related_name='room_type', verbose_name="Type de salle")

    class Meta:
        verbose_name = "Salle"
        verbose_name_plural = "Salles"


    def __str__(self):
        depts = ", ".join(str(d) for d in self.departements.all())
        return f"{self.room_number} ({self.room_type}) - {depts}"

class Grade(models.Model):
    name = models.CharField("Nom", max_length=20, unique=True)
    teachCours = models.BooleanField("Enseigne Cours", default=False)
    teachTD = models.BooleanField("Enseigne TD", default=False)
    teachTP = models.BooleanField("Enseigne TP", default=False)

    def __str__(self):
        return self.name

