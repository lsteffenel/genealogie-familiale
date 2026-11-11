from django.test import TestCase
from django.urls import reverse


class I18nTests(TestCase):
    def test_default_language_is_french(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Se connecter")
        self.assertContains(response, '<html lang="fr">')

    def test_accept_language_english(self):
        response = self.client.get(reverse("login"), HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Log in")
        self.assertContains(response, '<html lang="en">')

    def test_accept_language_italian(self):
        response = self.client.get(reverse("login"), HTTP_ACCEPT_LANGUAGE="it")
        self.assertContains(response, "Accedi")
        self.assertContains(response, '<html lang="it">')

    def test_accept_language_brazilian_portuguese(self):
        response = self.client.get(reverse("login"), HTTP_ACCEPT_LANGUAGE="pt-br")
        self.assertContains(response, "Entrar")
        self.assertContains(response, '<html lang="pt-br">')

    def test_set_language_view_switches_language_and_sets_cookie(self):
        response = self.client.post(
            reverse("set_language"), {"language": "en", "next": reverse("login")}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies["django_language"].value, "en")
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Log in")

    def test_language_switcher_present_on_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, reverse("set_language"))
        for name in ("Français", "Português (Brasil)", "English", "Italiano"):
            self.assertContains(response, name)
