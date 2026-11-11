from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from genealogy.models import Person


class HomeViewTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.person = Person.objects.create(first_name="Jean", last_name="Dupont")

    def test_home_redirects_to_linked_person(self):
        self.member.profile.person = self.person
        self.member.profile.save()
        self.client.force_login(self.member)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("person_detail", args=[self.person.pk]))

    def test_home_redirects_to_list_without_linked_person(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("person_list"))

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_nav_has_distinct_home_and_persons_links(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("person_list"))
        self.assertContains(response, f'href="{reverse("home")}"')
        self.assertContains(response, f'href="{reverse("person_list")}"')
