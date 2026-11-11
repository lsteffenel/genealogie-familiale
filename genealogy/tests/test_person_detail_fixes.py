import datetime

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from genealogy.models import EditProposal, Person, ProposalStatus, Union


class PersonDetailFixTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.client.force_login(self.member)
        self.husband = Person.objects.create(first_name="Jean", last_name="Dupont")
        self.wife = Person.objects.create(first_name="Marie", last_name="Martin")
        self.union = Union.objects.create(
            partner_a=self.husband, partner_b=self.wife,
            union_type=Union.UnionType.MARRIAGE,
            date=datetime.date(2001, 4, 26), place="Santa Maria",
        )

    def test_union_shows_other_partner_on_partner_b_page(self):
        response = self.client.get(reverse("person_detail", args=[self.wife.pk]))
        union, partner = response.context["unions"][0]
        self.assertEqual(partner, self.husband)
        self.assertContains(response, "Jean Dupont")

    def test_union_shows_other_partner_on_partner_a_page(self):
        response = self.client.get(reverse("person_detail", args=[self.husband.pk]))
        union, partner = response.context["unions"][0]
        self.assertEqual(partner, self.wife)
        self.assertContains(response, "Marie Martin")

    def test_only_pending_proposals_shown_on_person_detail(self):
        ct = ContentType.objects.get_for_model(Person)
        EditProposal.objects.create(
            content_type=ct, object_id=self.wife.pk,
            field_changes={"last_name": "Durand"}, proposed_by=self.member,
            status=ProposalStatus.APPROVED, reviewed_by=self.member,
        )
        EditProposal.objects.create(
            content_type=ct, object_id=self.wife.pk,
            field_changes={"birth_place": "Lyon"}, proposed_by=self.member,
        )
        response = self.client.get(reverse("person_detail", args=[self.wife.pk]))
        proposals = list(response.context["proposals"])
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].status, ProposalStatus.PENDING)
        self.assertContains(response, "birth_place")
        self.assertNotContains(response, "last_name")
