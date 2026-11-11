from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from genealogy.models import Media, Person, Union


class TreeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("member", password="secret123")
        self.client.force_login(self.user)
        self.grandpa = Person.objects.create(
            first_name="Albert", last_name="Dupont", birth_date="1930-05-01",
        )
        self.grandma = Person.objects.create(first_name="Simone", last_name="Martin")
        self.father = Person.objects.create(
            first_name="Jean", last_name="Dupont", birth_date="1960-01-15"
        )
        self.child = Person.objects.create(first_name="Lucie", last_name="Dupont")
        union1 = Union.objects.create(partner_a=self.grandpa, partner_b=self.grandma)
        union1.children.set([self.father])
        union2 = Union.objects.create(partner_a=self.father, partner_b=self.grandma)
        union2.children.set([self.child])

    def test_anonymous_redirected(self):
        self.client.logout()
        response = self.client.get(reverse("tree"))
        self.assertEqual(response.status_code, 302)

    def test_tree_shows_descendants_with_name_and_dates(self):
        response = self.client.get(reverse("tree_root", args=[self.grandpa.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Albert")
        self.assertContains(response, "Jean")
        self.assertContains(response, "Lucie")
        self.assertContains(response, "15/01/1960")

    def test_display_options_can_hide_name_and_dates(self):
        response = self.client.get(
            reverse("tree_root", args=[self.grandpa.pk]), {"name": "0", "dates": "0"}
        )
        self.assertNotContains(response, "Albert")
        self.assertNotContains(response, "15/01/1960")
        self.assertContains(response, "•••")

    def _add_photo(self):
        return Media.objects.create(
            person=self.grandpa, title="Albert",
            image=SimpleUploadedFile("albert.jpg", b"x", content_type="image/jpeg"),
        )

    def test_photo_shown_when_option_enabled(self):
        self._add_photo()
        response = self.client.get(reverse("tree_root", args=[self.grandpa.pk]))
        self.assertContains(response, "/media/photos/albert")

    def test_photo_hidden_when_option_disabled(self):
        self._add_photo()
        response = self.client.get(
            reverse("tree_root", args=[self.grandpa.pk]), {"photo": "0"}
        )
        self.assertNotContains(response, "/media/photos/")

    def test_root_selection_via_query_param(self):
        response = self.client.get(reverse("tree"), {"root": self.father.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jean")
        self.assertContains(response, "Lucie")


class ModeratorNotificationTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.moderator = User.objects.create_user(
            "mod", password="secret123", email="mod@example.com"
        )
        from genealogy.models import Role

        self.moderator.profile.role = Role.MODERATOR
        self.moderator.profile.save()
        self.person = Person.objects.create(first_name="Jean", last_name="Dupont")

    def test_submitting_proposal_emails_moderators(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("propose_person_edit", args=[self.person.pk]),
            {
                "first_name": "Jean", "last_name": "Dupont", "maiden_name": "",
                "gender": "", "birth_date": "", "birth_place": "Paris",
                "death_date": "", "death_place": "", "biography": "", "note": "acte",
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("mod@example.com", mail.outbox[0].to)
        self.assertIn("proposition #1", mail.outbox[0].subject)
        self.assertIn("birth_place", mail.outbox[0].body)

    def test_no_email_without_moderator_email(self):
        self.moderator.email = ""
        self.moderator.save()
        self.client.force_login(self.member)
        self.client.post(
            reverse("propose_person_edit", args=[self.person.pk]),
            {
                "first_name": "Jean", "last_name": "Dupont", "maiden_name": "",
                "gender": "", "birth_date": "", "birth_place": "Paris",
                "death_date": "", "death_place": "", "biography": "", "note": "",
            },
        )
        self.assertEqual(len(mail.outbox), 0)
