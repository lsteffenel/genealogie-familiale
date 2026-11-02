from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

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
        target = f"ajout d'un média « {data.get('title', '')} »"
        changes = f"personne #{data.get('person_id')}"
    else:
        target = f"{instance.content_type.model} #{instance.object_id}"
        changes = ", ".join(f"{field} → {value}" for field, value in instance.field_changes.items())
    send_mail(
        subject=f"[Généalogie] Nouvelle proposition #{instance.pk} à modérer",
        message=(
            f"{instance.proposed_by.username} propose {target}.\n"
            f"Détail : {changes}\n"
            f"{instance.note}\n\n"
            f"Modérez-la depuis l'admin ou la rubrique Modération du site."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )
