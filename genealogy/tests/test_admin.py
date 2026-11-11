from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from genealogy.models import EditProposal, Person, ProposalStatus, Role


class EditProposalAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="secret123")
        self.member = User.objects.create_user("member", password="secret123")
        self.person = Person.objects.create(first_name="Jean", last_name="Dupont")
        self.pending = EditProposal.objects.create(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=self.person.pk,
            field_changes={"birth_place": "Paris"},
            proposed_by=self.member,
        )
        self.approved = EditProposal.objects.create(
            content_type=ContentType.objects.get_for_model(Person),
            object_id=self.person.pk,
            field_changes={"birth_place": "Lyon"},
            proposed_by=self.member,
            status=ProposalStatus.APPROVED,
        )
        self.client.force_login(self.admin)
        self.changelist = reverse("admin:genealogy_editproposal_changelist")

    def test_changelist_shows_only_pending_by_default(self):
        response = self.client.get(self.changelist)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'field-status">En attente')
        self.assertNotContains(response, 'field-status">Approuvée')

    def test_changelist_all_statuses_shows_history(self):
        response = self.client.get(self.changelist, {"status": "all"})
        self.assertContains(response, 'field-status">En attente')
        self.assertContains(response, 'field-status">Approuvée')

    def test_changelist_approved_filter(self):
        response = self.client.get(self.changelist, {"status": "approved"})
        self.assertContains(response, 'field-status">Approuvée')
        self.assertNotContains(response, 'field-status">En attente')

    def test_quick_approve_button_only_on_pending_rows(self):
        response = self.client.get(self.changelist)
        self.assertContains(response, "✅")
        approve_url = reverse(
            "admin:genealogy_editproposal_approve", args=[self.pending.pk]
        )
        self.assertContains(response, approve_url)
        approved_url = reverse(
            "admin:genealogy_editproposal_approve", args=[self.approved.pk]
        )
        self.assertNotContains(response, approved_url)

    def test_approve_view_applies_pending_proposal(self):
        url = reverse("admin:genealogy_editproposal_approve", args=[self.pending.pk])
        response = self.client.post(url)
        self.assertRedirects(response, self.changelist)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ProposalStatus.APPROVED)
        self.person.refresh_from_db()
        self.assertEqual(self.person.birth_place, "Paris")

    def test_approve_view_refuses_already_reviewed(self):
        url = reverse("admin:genealogy_editproposal_approve", args=[self.approved.pk])
        self.client.post(url)
        self.approved.refresh_from_db()
        self.assertEqual(self.approved.status, ProposalStatus.APPROVED)

    def test_approve_view_requires_staff(self):
        self.client.force_login(self.member)
        url = reverse("admin:genealogy_editproposal_approve", args=[self.pending.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, ProposalStatus.PENDING)


class UserAdminAddTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin2", password="secret123")
        self.client.force_login(self.admin)

    def _post_add_user(self, person=None):
        data = {
            "username": "nouveau",
            "password1": "Secr3t-pass!",
            "password2": "Secr3t-pass!",
            "profile-TOTAL_FORMS": "1",
            "profile-INITIAL_FORMS": "0",
            "profile-MIN_NUM_FORMS": "0",
            "profile-MAX_NUM_FORMS": "1",
            "profile-0-role": "member",
        }
        if person is not None:
            data["profile-0-person"] = str(person.pk)
        return self.client.post(reverse("admin:auth_user_add"), data)

    def test_add_user_without_person(self):
        from genealogy.models import Profile

        response = self._post_add_user()
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="nouveau")
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_add_user_with_person_linked_at_once(self):
        from genealogy.models import Profile

        person = Person.objects.create(first_name="Jean", last_name="Dupont")
        response = self._post_add_user(person=person)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="nouveau")
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.person, person)
