import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from genealogy.models import EditProposal, Media, ProposalStatus, Role

TEST_MEDIA_ROOT = tempfile.mkdtemp()

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class MediaUploadProposalTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.moderator = User.objects.create_user("mod", password="secret123")
        self.moderator.profile.role = Role.MODERATOR
        self.moderator.profile.save()
        from genealogy.models import Person

        self.person = Person.objects.create(first_name="Jean", last_name="Dupont")

    def photo_file(self):
        return SimpleUploadedFile("photo.png", PNG_BYTES, content_type="image/png")

    def test_member_submits_local_photo_and_it_stays_pending(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.person.pk,
                "title": "Photo de mariage",
                "description": "1974",
                "google_photo_media_item_id": "",
                "note": "scannée",
                "image": self.photo_file(),
            },
        )
        self.assertRedirects(response, reverse("person_detail", args=[self.person.pk]))
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.action, EditProposal.Action.CREATE)
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertTrue(proposal.uploaded_file.name.startswith("proposals/"))
        self.assertEqual(proposal.new_object_data["title"], "Photo de mariage")
        self.assertEqual(Media.objects.count(), 0)

    def test_submission_requires_file_or_google_id(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.person.pk, "title": "Sans source",
                "description": "", "google_photo_media_item_id": "", "note": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EditProposal.objects.count(), 0)

    def test_google_photo_reference_without_file_is_accepted(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.person.pk, "title": "Photo album",
                "description": "", "google_photo_media_item_id": "ITEM123", "note": "",
            },
        )
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.new_object_data["google_photo_media_item_id"], "ITEM123")
        self.assertFalse(proposal.uploaded_file)

    def test_moderator_approval_creates_media_with_local_file(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.person.pk, "title": "Photo de mariage",
                "description": "", "google_photo_media_item_id": "", "note": "",
                "image": self.photo_file(),
            },
        )
        proposal = EditProposal.objects.get()
        self.client.force_login(self.moderator)
        self.client.post(
            reverse("proposal_review", args=[proposal.pk]),
            {"action": "approve", "comment": "OK"},
        )
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        media = Media.objects.get()
        self.assertEqual(media.title, "Photo de mariage")
        self.assertEqual(media.person, self.person)
        self.assertTrue(media.image.name.startswith("photos/"))

    def test_moderator_rejection_creates_nothing(self):
        self.client.force_login(self.member)
        self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.person.pk, "title": "Photo",
                "description": "", "google_photo_media_item_id": "ITEM9", "note": "",
            },
        )
        proposal = EditProposal.objects.get()
        self.client.force_login(self.moderator)
        self.client.post(
            reverse("proposal_review", args=[proposal.pk]),
            {"action": "reject", "comment": "floue"},
        )
        self.assertEqual(Media.objects.count(), 0)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.REJECTED)
