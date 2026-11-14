from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from genealogy.models import EditProposal, Media, Person, ProposalStatus

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

EDIT_POST = {
    "first_name": "Jean", "last_name": "Dupont", "maiden_name": "",
    "gender": "", "birth_date": "", "birth_place": "Paris, France",
    "death_date": "", "death_place": "", "biography": "", "note": "Vu sur l'acte",
}


class SelfEditAutoApproveTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member", password="secret123")
        self.own = Person.objects.create(first_name="Jean", last_name="Dupont", birth_place="Lyon")
        self.other = Person.objects.create(first_name="Marie", last_name="Martin")
        self.member.profile.person = self.own
        self.member.profile.save()
        self.client.force_login(self.member)

    def test_edit_own_person_is_applied_without_moderation(self):
        response = self.client.post(reverse("propose_person_edit", args=[self.own.pk]), EDIT_POST)
        self.assertRedirects(response, reverse("person_detail", args=[self.own.pk]))
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        self.assertEqual(proposal.reviewed_by, self.member)
        self.own.refresh_from_db()
        self.assertEqual(self.own.birth_place, "Paris, France")

    def test_edit_other_person_stays_pending(self):
        self.client.post(reverse("propose_person_edit", args=[self.other.pk]), {
            **EDIT_POST, "first_name": "Marie", "last_name": "Martin",
            "birth_place": "Paris, France",
        })
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.other.refresh_from_db()
        self.assertNotEqual(self.other.birth_place, "Paris, France")

    def test_media_on_own_person_is_published_immediately(self):
        response = self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.own.pk, "title": "Ma photo", "description": "", "note": "",
                "image": SimpleUploadedFile("photo.png", PNG_BYTES, content_type="image/png"),
            },
        )
        self.assertRedirects(response, reverse("person_detail", args=[self.own.pk]))
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(Media.objects.get().person, self.own)

    def test_media_on_other_person_stays_pending(self):
        self.client.post(
            reverse("propose_media_add"),
            {
                "person": self.other.pk, "title": "Photo", "description": "", "note": "",
                "image": SimpleUploadedFile("photo.png", PNG_BYTES, content_type="image/png"),
            },
        )
        proposal = EditProposal.objects.get()
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(Media.objects.count(), 0)
