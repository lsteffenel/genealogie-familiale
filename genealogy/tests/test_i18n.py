import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from genealogy.models import Person


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


class GenderedLabelsTests(TestCase):
    def test_labels_adapt_to_gender_in_portuguese(self):
        male = Person(first_name="Jean", last_name="Dupont", gender="M",
                      birth_date=datetime.date(1920, 5, 10),
                      death_date=datetime.date(1990, 1, 1))
        female = Person(first_name="Marie", last_name="Martin", gender="F",
                        birth_date=datetime.date(1922, 3, 15), maiden_name="Durand")
        other = Person(first_name="Alex", last_name="Bernard", gender="X",
                       birth_date=datetime.date(1930, 1, 1))
        with translation.override("pt-br"):
            self.assertIn("Nascido em", male.born_label)
            self.assertIn("Falecido em", male.died_label)
            self.assertIn("Nascida em", female.born_label)
            self.assertIn("nascida Durand", female.maiden_label)
            self.assertIn("Nascido/a em", other.born_label)

    def test_labels_adapt_to_gender_in_italian(self):
        male = Person(first_name="Jean", last_name="Dupont", gender="M",
                      birth_date=datetime.date(1920, 5, 10))
        female = Person(first_name="Marie", last_name="Martin", gender="F",
                        birth_date=datetime.date(1922, 3, 15))
        with translation.override("it"):
            self.assertIn("Nato il", male.born_label)
            self.assertIn("Nata il", female.born_label)

    def test_labels_neutral_when_gender_unknown(self):
        person = Person(first_name="Jean", last_name="Dupont",
                        birth_date=datetime.date(1920, 5, 10))
        with translation.override("pt-br"):
            self.assertIn("Nascido/a em", person.born_label)
        with translation.override("fr"):
            self.assertIn("Né(e) le", person.born_label)

    def test_empty_labels_without_dates(self):
        person = Person(first_name="Jean", last_name="Dupont")
        self.assertEqual(person.born_label, "")
        self.assertEqual(person.died_label, "")
        self.assertEqual(person.maiden_label, "")
