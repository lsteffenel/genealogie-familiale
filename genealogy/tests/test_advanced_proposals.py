from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from genealogy.models import EditProposal, Event, Person, ProposalStatus, Role, Union


class AdvancedProposalTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.moderator = User.objects.create_user("mod", password="secret123")
        self.moderator.profile.role = Role.MODERATOR
        self.moderator.profile.save()
        self.person = Person.objects.create(
            first_name="Jean", last_name="Dupont", birth_place="Lyon"
        )
        self.partner = Person.objects.create(first_name="Marie", last_name="Martin")
        self.client.force_login(self.member)
        self.base_data = {
            "first_name": "Jean", "last_name": "Dupont", "maiden_name": "",
            "gender": "", "birth_date": "", "birth_place": "Lyon",
            "death_date": "", "death_place": "", "biography": "", "note": "",
            "adv_kind": "",
        }

    def post(self, **extra):
        data = {**self.base_data, **extra}
        return self.client.post(reverse("propose_person_edit", args=[self.person.pk]), data)

    def test_event_proposal_creates_pending_create_proposal(self):
        self.post(
            adv_kind="event", event_type="baptism", title="Baptême à Lyon",
            date="1920-05-10", place="Lyon", description="",
        )
        proposal = EditProposal.objects.get(action=EditProposal.Action.CREATE)
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(proposal.new_object_data["model"], "event")
        self.assertEqual(proposal.new_object_data["event_type"], "baptism")
        self.assertEqual(proposal.new_object_data["title"], "Baptême à Lyon")
        self.assertEqual(proposal.new_object_data["person_id"], self.person.pk)
        self.assertEqual(Event.objects.count(), 0)

    def test_event_proposal_applied_by_moderator_creates_event(self):
        self.post(adv_kind="event", event_type="baptism", title="Baptême à Lyon",
                  date="1920-05-10", place="Lyon", description="")
        proposal = EditProposal.objects.get(action=EditProposal.Action.CREATE)
        self.client.force_login(self.moderator)
        self.client.post(reverse("proposal_review", args=[proposal.pk]), {"action": "approve"})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        event = Event.objects.get()
        self.assertEqual(event.person, self.person)
        self.assertEqual(event.event_type, "baptism")
        self.assertEqual(str(event.date), "1920-05-10")

    def test_union_proposal_applied_creates_union(self):
        self.post(adv_kind="union", partner=str(self.partner.pk), union_type="marriage",
                  date="1945-06-01", place="Paris", notes="")
        proposal = EditProposal.objects.get(action=EditProposal.Action.CREATE)
        self.assertEqual(proposal.new_object_data["model"], "union")
        self.assertEqual(proposal.new_object_data["partner_id"], self.partner.pk)
        self.client.force_login(self.moderator)
        self.client.post(reverse("proposal_review", args=[proposal.pk]), {"action": "approve"})
        union = Union.objects.get()
        self.assertEqual(union.partner_a, self.person)
        self.assertEqual(union.partner_b, self.partner)
        self.assertEqual(union.union_type, "marriage")

    def test_event_without_title_is_rejected(self):
        self.post(adv_kind="event", event_type="baptism", title="", date="1920-05-10")
        self.assertEqual(EditProposal.objects.count(), 0)

    def test_union_without_partner_is_rejected(self):
        self.post(adv_kind="union", union_type="marriage", date="1945-06-01")
        self.assertEqual(EditProposal.objects.count(), 0)

    def test_advanced_section_optional(self):
        response = self.post()
        self.assertEqual(EditProposal.objects.count(), 0)  # aucune modif de base non plus
        self.post(birth_place="Paris")
        self.assertEqual(EditProposal.objects.count(), 1)
        self.assertEqual(
            EditProposal.objects.get().action, EditProposal.Action.EDIT
        )

    def test_moderation_list_displays_event_proposal(self):
        self.post(adv_kind="event", event_type="census", title="Recensement 1936")
        self.client.force_login(self.moderator)
        response = self.client.get(reverse("proposal_list"))
        self.assertContains(response, "Recensement 1936")
        self.assertContains(response, "event")
