import os

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    MEMBER = "member", _("Membre")
    MODERATOR = "moderator", _("Modérateur")
    ADMIN = "admin", _("Administrateur")


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER
    )
    person = models.OneToOneField(
        "Person", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="account",
        help_text=_("Personne de l'arbre correspondant à ce compte (évite les doublons)"),
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_moderator(self):
        return self.role in (Role.MODERATOR, Role.ADMIN)


class Person(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", _("Homme")
        FEMALE = "F", _("Femme")
        OTHER = "X", _("Autre")

    first_name = models.CharField(max_length=150, verbose_name=_("Prénom"))
    last_name = models.CharField(max_length=150, verbose_name=_("Nom"))
    maiden_name = models.CharField(max_length=150, blank=True, verbose_name=_("Nom de jeune fille"))
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True, verbose_name=_("Sexe"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Date de naissance"))
    birth_place = models.CharField(max_length=255, blank=True, verbose_name=_("Lieu de naissance"))
    death_date = models.DateField(null=True, blank=True, verbose_name=_("Date de décès"))
    death_place = models.CharField(max_length=255, blank=True, verbose_name=_("Lieu de décès"))
    biography = models.TextField(blank=True, verbose_name=_("Biographie"))
    google_photo_media_item_id = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Identifiant de la photo dans l'album Google Photos partagé"),
    )
    gedcom_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True,
        help_text=_("Identifiant d'origine dans le fichier GEDCOM importé"),
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
                _("La date de décès ne peut pas être antérieure à la date de naissance.")
            )


class Union(models.Model):
    class UnionType(models.TextChoices):
        MARRIAGE = "marriage", _("Mariage")
        PACS = "pacs", _("PACS")
        COHABITATION = "cohabitation", _("Concubinage")
        OTHER = "other", _("Autre")

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
            raise ValidationError(_("Les deux partenaires doivent être des personnes différentes."))


class Event(models.Model):
    class EventType(models.TextChoices):
        DIPLOMA = "diploma", _("Diplôme (graduation)")
        JOB = "job", _("Métier")
        RESIDENCE = "residence", _("Résidence")
        ANECDOTE = "anecdote", _("Anecdote / Histoire")
        AWARD = "award", _("Distinction")
        ADOPTION = "adoption", _("Adoption")
        BAPTISM = "baptism", _("Baptême")
        CHILD_BAPTISM = "child_baptism", _("Baptême d'enfant")
        CONFIRMATION = "confirmation", _("Confirmation")
        BAR_MITZVAH = "bar_mitzvah", _("Bar-mitsva")
        BAS_MITZVAH = "bas_mitzvah", _("Bas-mitsva")
        BLESSING = "blessing", _("Bénédiction")
        BURIAL = "burial", _("Inhumation")
        CENSUS = "census", _("Recensement")
        CREMATION = "cremation", _("Crémation")
        EMIGRATION = "emigration", _("Émigration")
        IMMIGRATION = "immigration", _("Immigration")
        NATURALIZATION = "naturalization", _("Naturalisation")
        ORDINATION = "ordination", _("Ordination")
        PROBATE = "probate", _("Acte de décès (probate)")
        RELIGION = "religion", _("Religion")
        RETIREMENT = "retirement", _("Retraite")
        TITLE = "title", _("Titre")
        NOBILITY = "nobility", _("Noblesse")
        OTHER = "other", _("Autre")

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
        help_text=_("Identifiant du média dans Google Photos (affichage via l'API)"),
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
            raise ValidationError(_("Un média doit être rattaché à une personne ou à un événement."))
        if not self.image and not self.google_photo_media_item_id:
            raise ValidationError(
                _("Un média doit contenir une image uploadée ou un identifiant Google Photos.")
            )


class ProposalStatus(models.TextChoices):
    PENDING = "pending", _("En attente")
    APPROVED = "approved", _("Approuvée")
    REJECTED = "rejected", _("Rejetée")


class EditProposal(models.Model):
    class Action(models.TextChoices):
        EDIT = "edit", _("Modification")
        CREATE = "create", _("Ajout")

    action = models.CharField(
        max_length=10, choices=Action.choices, default=Action.EDIT
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    field_changes = models.JSONField(
        default=dict, blank=True,
        help_text=_("Dictionnaire {champ: nouvelle_valeur} proposé par le membre"),
    )
    new_object_data = models.JSONField(
        null=True, blank=True,
        help_text=_("Pour action=create : données du nouvel objet (ex. média à créer)"),
    )
    uploaded_file = models.FileField(
        upload_to="proposals/", null=True, blank=True,
        help_text=_("Fichier uploadé par le membre, rattaché au nouvel objet à validation"),
    )
    note = models.TextField(
        blank=True, help_text=_("Commentaire du membre accompagnant sa proposition")
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
        if self.action == EditProposal.Action.CREATE:
            return _("Proposition #%(pk)s : ajout (%(status)s)") % {
                "pk": self.pk, "status": self.get_status_display(),
            }
        return _("Proposition #%(pk)s sur %(model)s #%(object_id)s (%(status)s)") % {
            "pk": self.pk, "model": self.content_type.model,
            "object_id": self.object_id, "status": self.get_status_display(),
        }

    def apply(self, reviewer):
        from django.utils import timezone

        if self.status != ProposalStatus.PENDING:
            raise ValidationError(_("Seule une proposition en attente peut être appliquée."))
        if self.action == EditProposal.Action.CREATE:
            data = self.new_object_data or {}
            model = data.get("model")
            if model == "media":
                media = Media(
                    person_id=data.get("person_id"),
                    title=data.get("title", ""),
                    description=data.get("description", ""),
                    google_photo_media_item_id=data.get("google_photo_media_item_id", ""),
                )
                if self.uploaded_file:
                    self.uploaded_file.open("rb")
                    media.image.save(
                        os.path.basename(self.uploaded_file.name),
                        ContentFile(self.uploaded_file.read()),
                        save=False,
                    )
                media.full_clean()
                media.save()
            elif model == "event":
                event = Event(
                    person_id=data.get("person_id"),
                    event_type=data.get("event_type", Event.EventType.OTHER),
                    title=data.get("title", ""),
                    date=data.get("date") or None,
                    place=data.get("place", ""),
                    description=data.get("description", ""),
                    created_by=reviewer,
                )
                event.full_clean()
                event.save()
            elif model == "union":
                union = Union(
                    partner_a_id=data.get("person_id"),
                    partner_b_id=data.get("partner_id"),
                    union_type=data.get("union_type", Union.UnionType.OTHER),
                    date=data.get("date") or None,
                    place=data.get("place", ""),
                    notes=data.get("notes", ""),
                )
                union.full_clean()
                union.save()
            else:
                raise ValidationError(_("Type d'objet à créer non supporté."))
        else:
            for field, value in self.field_changes.items():
                if not hasattr(self.target, field):
                    raise ValidationError(_("Champ inconnu : %(field)s") % {"field": field})
                setattr(self.target, field, value)
            self.target.save()
        self.status = ProposalStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    def reject(self, reviewer, comment=""):
        from django.utils import timezone

        if self.status != ProposalStatus.PENDING:
            raise ValidationError(_("Seule une proposition en attente peut être rejetée."))
        self.status = ProposalStatus.REJECTED
        self.reviewed_by = reviewer
        self.review_comment = comment
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "review_comment", "reviewed_at"])
