from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from genealogy.models import (
    EditProposal,
    Event,
    Media,
    Person,
    Profile,
    ProposalStatus,
    Role,
    Union,
)


class ProfileTests(TestCase):
    def test_profile_created_with_user_defaults_to_member(self):
        user = User.objects.create_user("alice", password="secret123")
        self.assertEqual(user.profile.role, Role.MEMBER)
        self.assertFalse(user.profile.is_moderator)

    def test_moderator_flag(self):
        user = User.objects.create_user("bob", password="secret123")
        user.profile.role = Role.MODERATOR
        user.profile.save()
        self.assertTrue(user.profile.is_moderator)


class PersonTests(TestCase):
    def test_death_before_birth_is_invalid(self):
        person = Person(
            first_name="Jean", last_name="Dupont",
            birth_date="1950-01-12", death_date="1949-01-01",
        )
        with self.assertRaises(ValidationError):
            person.full_clean()


class UnionTests(TestCase):
    def test_same_partner_is_invalid(self):
        person = Person.objects.create(first_name="Jean", last_name="Dupont")
        union = Union(partner_a=person, partner_b=person)
        with self.assertRaises(ValidationError):
            union.full_clean()


class MediaTests(TestCase):
    def test_media_requires_target_and_source(self):
        person = Person.objects.create(first_name="Jean", last_name="Dupont")
        with self.assertRaises(ValidationError):
            Media(title="Photo sans cible").full_clean()
        with self.assertRaises(ValidationError):
            Media(person=person, title="Sans source").full_clean()
        media = Media(person=person, title="OK", google_photo_media_item_id="abc123")
        media.full_clean()


class EditProposalTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.moderator = User.objects.create_user("mod", password="secret123")
        self.moderator.profile.role = Role.MODERATOR
        self.moderator.profile.save()
        self.person = Person.objects.create(first_name="Jean", last_name="Dupont")

    def make_proposal(self):
        from django.contrib.contenttypes.models import ContentType

        return EditProposal.objects.create(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=self.person.pk,
            field_changes={"birth_place": "Paris, France"},
            proposed_by=self.member,
        )

    def test_apply_updates_target_and_marks_approved(self):
        proposal = self.make_proposal()
        proposal.apply(self.moderator)
        self.person.refresh_from_db()
        self.assertEqual(self.person.birth_place, "Paris, France")
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        self.assertEqual(proposal.reviewed_by, self.moderator)
        self.assertIsNotNone(proposal.reviewed_at)

    def test_reject_marks_proposal_without_touching_target(self):
        proposal = self.make_proposal()
        proposal.reject(self.moderator, comment="Source non vérifiée")
        self.person.refresh_from_db()
        self.assertEqual(self.person.birth_place, "")
        self.assertEqual(proposal.status, ProposalStatus.REJECTED)
        self.assertEqual(proposal.review_comment, "Source non vérifiée")

    def test_cannot_apply_twice(self):
        proposal = self.make_proposal()
        proposal.apply(self.moderator)
        with self.assertRaises(ValidationError):
            proposal.apply(self.moderator)

    def test_unknown_field_rejected(self):
        from django.contrib.contenttypes.models import ContentType

        proposal = EditProposal.objects.create(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=self.person.pk,
            field_changes={"champ_inconnu": "x"},
            proposed_by=self.member,
        )
        with self.assertRaises(ValidationError):
            proposal.apply(self.moderator)


class EventTests(TestCase):
    def test_event_types_cover_third_party_info(self):
        person = Person.objects.create(first_name="Jean", last_name="Dupont")
        event = Event.objects.create(
            person=person, event_type=Event.EventType.JOB, title="Ingénieur"
        )
        self.assertEqual(event.event_type, "job")
