from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from genealogy.google_photos import get_media_item_base_url
from genealogy.models import Media, Person


class GooglePhotosServiceTests(TestCase):
    def test_returns_none_without_credentials(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(get_media_item_base_url("ABC123"))

    def test_returns_none_for_empty_id(self):
        self.assertIsNone(get_media_item_base_url(""))

    def test_builds_sized_url_from_api_response(self):
        env = {
            "GOOGLE_PHOTOS_CLIENT_ID": "id",
            "GOOGLE_PHOTOS_CLIENT_SECRET": "secret",
            "GOOGLE_PHOTOS_REFRESH_TOKEN": "refresh",
        }
        fake_response = mock.Mock(status_code=200)
        fake_response.json.return_value = {"baseUrl": "https://lh3.googleusercontent.com/abc"}
        with mock.patch.dict("os.environ", env, clear=True), mock.patch(
            "genealogy.google_photos.Request"
        ), mock.patch(
            "google.oauth2.credentials.Credentials.refresh"
        ), mock.patch(
            "genealogy.google_photos.requests.get", return_value=fake_response
        ) as mock_get:
            url = get_media_item_base_url("ITEM1")
        self.assertEqual(url, "https://lh3.googleusercontent.com/abc=w800-h600")
        mock_get.assert_called_once()

    def test_returns_none_on_api_error(self):
        env = {
            "GOOGLE_PHOTOS_CLIENT_ID": "id",
            "GOOGLE_PHOTOS_CLIENT_SECRET": "secret",
            "GOOGLE_PHOTOS_REFRESH_TOKEN": "refresh",
        }
        with mock.patch.dict("os.environ", env, clear=True), mock.patch(
            "google.oauth2.credentials.Credentials.refresh"
        ), mock.patch(
            "genealogy.google_photos.requests.get",
            return_value=mock.Mock(status_code=403),
        ):
            self.assertIsNone(get_media_item_base_url("ITEM2"))


class GooglePhotosDisplayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("member", password="secret123")
        self.client.force_login(self.user)
        self.person = Person.objects.create(
            first_name="Jean", last_name="Dupont",
            google_photo_media_item_id="ITEM_PERSO",
        )

    def test_detail_page_shows_google_photo_when_resolved(self):
        with mock.patch(
            "genealogy.views.get_media_item_base_url",
            return_value="https://photos.example/abc=w800-h600",
        ):
            response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertContains(response, "https://photos.example/abc=w800-h600")

    def test_detail_page_falls_back_gracefully_without_config(self):
        with mock.patch(
            "genealogy.views.get_media_item_base_url", return_value=None
        ):
            response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertContains(response, "identifiants API non configurés")

    def test_media_list_shows_google_photos(self):
        Media.objects.create(
            person=self.person, title="Mariage",
            google_photo_media_item_id="ITEM_MEDIA",
        )
        with mock.patch(
            "genealogy.views.get_media_item_base_url",
            return_value="https://photos.example/xyz=w800-h600",
        ):
            response = self.client.get(reverse("person_detail", args=[self.person.pk]))
        self.assertContains(response, "https://photos.example/xyz=w800-h600")
        self.assertContains(response, "Mariage")
