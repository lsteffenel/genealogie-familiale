from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from genealogy.models import Person, SiteConfiguration


class SiteConfigurationTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.client.force_login(self.member)
        self.alice = Person.objects.create(first_name="Alice", last_name="Durand")
        self.bob = Person.objects.create(first_name="Bob", last_name="Durand")
        self.claire = Person.objects.create(first_name="Claire", last_name="Martin")

    def test_default_root_is_first_person_alphabetically(self):
        response = self.client.get(reverse("tree"))
        # ordering is last_name, first_name: Durand (Alice) comes first
        self.assertEqual(response.context["root"], self.alice)

    def test_configured_default_root_is_used(self):
        config = SiteConfiguration.get()
        config.default_tree_root = self.claire
        config.save()
        response = self.client.get(reverse("tree"))
        self.assertEqual(response.context["root"], self.claire)

    def test_explicit_root_param_overrides_default(self):
        config = SiteConfiguration.get()
        config.default_tree_root = self.claire
        config.save()
        response = self.client.get(reverse("tree"), {"root": self.alice.pk})
        self.assertEqual(response.context["root"], self.alice)

    def test_home_banner_displayed_on_person_detail(self):
        config = SiteConfiguration.get()
        config.home_page_html = "<p>Bienvenue !</p>"
        config.save()
        response = self.client.get(reverse("person_detail", args=[self.alice.pk]))
        self.assertContains(response, "<p>Bienvenue !</p>")
        self.assertContains(response, "home-content")

    def test_persons_banner_displayed_above_list(self):
        config = SiteConfiguration.get()
        config.persons_page_html = "<p>Liste des familles</p>"
        config.save()
        response = self.client.get(reverse("person_list"))
        self.assertContains(response, "<p>Liste des familles</p>")
        self.assertContains(response, "home-content")

    def test_no_banner_by_default(self):
        response = self.client.get(reverse("person_list"))
        self.assertNotContains(response, "home-content")
        response = self.client.get(reverse("person_detail", args=[self.alice.pk]))
        self.assertNotContains(response, "home-content")

    def test_list_shows_families_first(self):
        response = self.client.get(reverse("person_list"))
        self.assertEqual(response.context["mode"], "families")
        self.assertContains(response, "Durand")
        self.assertContains(response, "Martin")
        self.assertNotContains(response, "Alice")

    def test_family_param_shows_individuals_of_family(self):
        response = self.client.get(reverse("person_list"), {"family": "Durand"})
        self.assertEqual(response.context["mode"], "family")
        self.assertContains(response, "Alice")
        self.assertContains(response, "Bob")
        self.assertNotContains(response, "Claire")

    def test_search_still_returns_flat_results(self):
        response = self.client.get(reverse("person_list"), {"q": "alice"})
        self.assertEqual(response.context["mode"], "search")
        self.assertContains(response, "Alice")
        self.assertNotContains(response, "Bob")

    def test_str_methods_return_real_strings(self):
        from genealogy.models import EditProposal

        config = SiteConfiguration.get()
        self.assertIs(type(str(config)), str)
        proposal = EditProposal.objects.create(
            action=EditProposal.Action.CREATE, proposed_by=self.member
        )
        self.assertIs(type(str(proposal)), str)
