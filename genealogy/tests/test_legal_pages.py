from django.test import TestCase
from django.urls import reverse


class LegalPagesTests(TestCase):
    def test_privacy_page_is_public(self):
        response = self.client.get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Politique de confidentialité")

    def test_terms_page_is_public(self):
        response = self.client.get(reverse("terms"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conditions d'utilisation")

    def test_footer_links_present_on_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, reverse("privacy"))
        self.assertContains(response, reverse("terms"))

    def test_pages_available_in_english(self):
        response = self.client.get(reverse("privacy"), HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Privacy policy")
        response = self.client.get(reverse("terms"), HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Terms of use")
