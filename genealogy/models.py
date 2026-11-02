from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models


class Role(models.TextChoices):
    MEMBER = "member", "Membre"
    MODERATOR = "moderator", "Modérateur"
    ADMIN = "admin", "Administrateur"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_moderator(self):
        return self.role in (Role.MODERATOR, Role.ADMIN)


class Person(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Homme"
        FEMALE = "F", "Femme"
        OTHER = "X", "Autre"

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    maiden_name = models.CharField(max_length=150, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=255, blank=True)
    death_date = models.DateField(null=True, blank=True)
    death_place = models.CharField(max_length=255, blank=True)
    biography = models.TextField(blank=True)
    google_photo_media_item_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Identifiant de la photo dans l'album Google Photos partagé",
    )
    gedcom_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        help_text="Identifiant d'origine dans le fichier GEDCOM importé",
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="persons_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        if self.birth_date and self.death_date and self.death_date < self.birth_date:
            raise ValidationError(
                "La date de décès ne peut pas être antérieure à la date de naissance."
            )


class Union(models.Model):
    class UnionType(models.TextChoices):
        MARRIAGE = "marriage", "Mariage"
        PACS = "pacs", "PACS"
        COHABITATION = "cohabitation", "Concubinage"
        OTHER = "other", "Autre"

    partner_a = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="unions_as_a"
    )
    partner_b = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="unions_as_b"
    )
    union_type = models.CharField(
        max_length=20, choices=UnionType.choices, default=UnionType.MARRIAGE
    )
    date = models.DateField(null=True, blank=True)
    place = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    gedcom_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    children = models.ManyToManyField(
        Person, related_name="parent_unions", blank=True
    )

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.partner_a} & {self.partner_b}"

    def clean(self):
        if self.partner_a_id and self.partner_b_id and self.partner_a_id == self.partner_b_id:
            raise ValidationError("Les deux partenaires doivent être des personnes différentes.")


class Event(models.Model):
    class EventType(models.TextChoices):
        DIPLOMA = "diploma", "Diplôme"
        JOB = "job", "Métier"
        RESIDENCE = "residence", "Résidence"
        ANECDOTE = "anecdote", "Anecdote / Histoire"
        AWARD = "award", "Distinction"
        OTHER = "other", "Autre"

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    title = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    place = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="events_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]

    def __str__(self):
        return f"{self.get_event_type_display()} : {self.title} ({self.person})"


class Media(models.Model):
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="media", null=True, blank=True
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="media", null=True, blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="photos/", blank=True)
    google_photo_media_item_id = models.CharField(
        max_length=255, blank=True,
        help_text="Identifiant du média dans Google Photos (affichage via l'API)",
    )
    uploaded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="media_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if not self.person and not self.event:
            raise ValidationError("Un média doit être rattaché à une personne ou à un événement.")
        if not self.image and not self.google_photo_media_item_id:
            raise ValidationError(
                "Un média doit contenir une image uploadée ou un identifiant Google Photos."
            )


class ProposalStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    APPROVED = "approved", "Approuvée"
    REJECTED = "rejected", "Rejetée"


class EditProposal(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    field_changes = models.JSONField(
        help_text="Dictionnaire {champ: nouvelle_valeur} proposé par le membre"
    )
    note = models.TextField(
        blank=True, help_text="Commentaire du membre accompagnant sa proposition"
    )
    proposed_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="proposals_made"
    )
    status = models.CharField(
        max_length=20, choices=ProposalStatus.choices, default=ProposalStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="proposals_reviewed",
    )
    review_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Proposition #{self.pk} sur {self.content_type.model} #{self.object_id} ({self.get_status_display()})"

    def apply(self, reviewer):
        from django.utils import timezone

        if self.status != ProposalStatus.PENDING:
            raise ValidationError("Seule une proposition en attente peut être appliquée.")
        for field, value in self.field_changes.items():
            if not hasattr(self.target, field):
                raise ValidationError(f"Champ inconnu : {field}")
            setattr(self.target, field, value)
        self.target.save()
        self.status = ProposalStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    def reject(self, reviewer, comment=""):
        from django.utils import timezone

        if self.status != ProposalStatus.PENDING:
            raise ValidationError("Seule une proposition en attente peut être rejetée.")
        self.status = ProposalStatus.REJECTED
        self.reviewed_by = reviewer
        self.review_comment = comment
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "review_comment", "reviewed_at"])
