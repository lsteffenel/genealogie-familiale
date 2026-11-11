from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    ALLOWED_HOSTS=["genealogia.lsteffenel.fr"],
    CSRF_TRUSTED_ORIGINS=["https://genealogia.lsteffenel.fr"],
)
class CsrfBehindHttpsProxyTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _post_login(self, origin):
        self.client.get(reverse("login"), secure=True, HTTP_HOST="genealogia.lsteffenel.fr")
        token = self.client.cookies["csrftoken"].value
        return self.client.post(
            reverse("login"),
            {"username": "x", "password": "y", "csrfmiddlewaretoken": token},
            secure=True,
            HTTP_ORIGIN=origin,
            HTTP_HOST="genealogia.lsteffenel.fr",
        )

    def test_login_post_accepted_with_https_origin(self):
        response = self._post_login("https://genealogia.lsteffenel.fr")
        # 200 = formulaire réaffiché (échec de connexion normal), pas 403 CSRF
        self.assertEqual(response.status_code, 200)

    def test_login_post_rejected_with_foreign_origin(self):
        response = self._post_login("https://evil.example.com")
        self.assertEqual(response.status_code, 403)
