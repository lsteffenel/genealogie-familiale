from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext as _

from .models import EditProposal, Profile, ProposalStatus, Role


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={"role": Role.MEMBER})


@receiver(post_save, sender=EditProposal)
def notify_moderators_on_new_proposal(sender, instance, created, **kwargs):
    if not created or instance.status != ProposalStatus.PENDING:
        return
    recipients = list(
        User.objects.filter(
            profile__role__in=[Role.MODERATOR, Role.ADMIN], is_active=True
        )
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients:
        return
    if instance.action == EditProposal.Action.CREATE:
        data = instance.new_object_data or {}
        target = _("ajout d'un média « %(title)s »") % {"title": data.get("title", "")}
        changes = _("personne #%(person_id)s") % {"person_id": data.get("person_id")}
    else:
        target = f"{instance.content_type.model} #{instance.object_id}"
        changes = ", ".join(f"{field} → {value}" for field, value in instance.field_changes.items())
    send_mail(
        subject=_("[Généalogie] Nouvelle proposition #%(pk)s à modérer") % {"pk": instance.pk},
        message=_(
            "%(username)s propose %(target)s.\n"
            "Détail : %(changes)s\n"
            "%(note)s\n\n"
            "Modérez-la depuis l'admin ou la rubrique Modération du site."
        ) % {
            "username": instance.proposed_by.username,
            "target": target,
            "changes": changes,
            "note": instance.note,
        },
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )
