from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from genealogy.models import EditProposal, Person, ProposalStatus, Role


class BaseViewTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.moderator = User.objects.create_user("mod", password="secret123")
        self.moderator.profile.role = Role.MODERATOR
        self.moderator.profile.save()
        self.person = Person.objects.create(
            first_name="Jean", last_name="Dupont", birth_place="Lyon"
        )


class AccessTests(BaseViewTests):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("person_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_anonymous_has_no_access_to_any_data_route(self):
        from django.contrib.contenttypes.models import ContentType

        proposal = EditProposal.objects.create(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=self.person.pk,
            field_changes={"birth_place": "Paris"},
            proposed_by=self.member,
        )
        protected_urls = [
            reverse("person_list"),
            reverse("person_detail", args=[self.person.pk]),
            reverse("propose_person_edit", args=[self.person.pk]),
            reverse("propose_media_add"),
            reverse("proposal_list"),
            reverse("proposal_review", args=[proposal.pk]),
            "/media/photos/test.jpg",
        ]
        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    def test_authenticated_member_can_reach_media_route(self):
        self.client.force_login(self.member)
        response = self.client.get("/media/photos/test.jpg")
        self.assertNotEqual(response.status_code, 302)
        self.assertEqual(response.status_code, 404)

    def test_member_can_see_person_list_and_detail(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("person_list")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("person_detail", args=[self.person.pk])).status_code, 200
        )

    def test_search_filters_by_name(self):
        Person.objects.create(first_name="Marie", last_name="Martin")
        self.client.force_login(self.member)
        response = self.client.get(reverse("person_list"), {"q": "martin"})
        self.assertContains(response, "Martin")
        self.assertNotContains(response, "Dupont")


class ProposalSubmissionTests(BaseViewTests):
    def test_member_submits_proposal_and_it_stays_pending(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("propose_person_edit", args=[self.person.pk]),
            {
                "first_name": "Jean", "last_name": "Dupont", "maiden_name": "",
                "gender": "", "birth_date": "", "birth_place": "Paris, France",
                "death_date": "", "death_place": "", "biography": "", "note": "Vu sur l'acte",
            },
        )
        self.assertRedirects(response, reverse("person_detail", args=[self.person.pk]))
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(proposal.field_changes, {"birth_place": "Paris, France"})
        self.assertEqual(proposal.note, "Vu sur l'acte")
        self.person.refresh_from_db()
        self.assertEqual(self.person.birth_place, "Lyon")

    def test_no_change_creates_no_proposal(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("propose_person_edit", args=[self.person.pk]),
            {
                "first_name": "Jean", "last_name": "Dupont", "maiden_name": "",
                "gender": "", "birth_date": "", "birth_place": "Lyon",
                "death_date": "", "death_place": "", "biography": "", "note": "",
            },
        )
        self.assertEqual(EditProposal.objects.count(), 0)


class ModerationTests(BaseViewTests):
    def setUp(self):
        super().setUp()
        self.proposal = EditProposal.objects.create(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=self.person.pk,
            field_changes={"birth_place": "Paris, France"},
            proposed_by=self.member,
        )

    def test_member_cannot_access_moderation(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("proposal_list"))
        self.assertEqual(response.status_code, 302)

    def test_moderator_sees_pending_proposal(self):
        self.client.force_login(self.moderator)
        response = self.client.get(reverse("proposal_list"))
        self.assertContains(response, "birth_place")

    def test_moderator_approves_and_change_is_applied(self):
        self.client.force_login(self.moderator)
        response = self.client.post(
            reverse("proposal_review", args=[self.proposal.pk]),
            {"action": "approve", "comment": "OK"},
        )
        self.assertRedirects(response, reverse("proposal_list"))
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProposalStatus.APPROVED)
        self.person.refresh_from_db()
        self.assertEqual(self.person.birth_place, "Paris, France")

    def test_moderator_rejects_and_target_unchanged(self):
        self.client.force_login(self.moderator)
        self.client.post(
            reverse("proposal_review", args=[self.proposal.pk]),
            {"action": "reject", "comment": "Source douteuse"},
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProposalStatus.REJECTED)
        self.assertEqual(self.proposal.review_comment, "Source douteuse")
        self.person.refresh_from_db()
        self.assertEqual(self.person.birth_place, "Lyon")
