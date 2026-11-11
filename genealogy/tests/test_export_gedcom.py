import datetime
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from genealogy.models import Event, Person, Union


class ExportGedcomTests(TestCase):
    def setUp(self):
        self.jean = Person.objects.create(
            first_name="Jean", last_name="Dupont", gender="M",
            birth_date=datetime.date(1950, 1, 12), birth_place="Paris",
            gedcom_id="I1",
        )
        self.marie = Person.objects.create(
            first_name="Marie", last_name="Martin", maiden_name="Durand",
            gender="F", gedcom_id="I2",
        )
        self.union = Union.objects.create(
            partner_a=self.jean, partner_b=self.marie,
            union_type=Union.UnionType.MARRIAGE,
            date=datetime.date(1974, 7, 14), place="Lyon", gedcom_id="F1",
        )
        self.union.children.add(self.jean)
        Event.objects.create(
            person=self.jean, event_type=Event.EventType.NAME_CHANGE,
            title="Changement de nom", date=datetime.date(1961, 1, 1),
            place="Rome",
        )

    def test_export_command_content(self):
        out = StringIO()
        call_command("export_gedcom", stdout=out)
        ged = out.getvalue()
        self.assertIn("0 HEAD", ged)
        self.assertIn("0 @I1@ INDI", ged)
        self.assertIn("1 NAME Jean /Dupont/", ged)
        self.assertIn("1 SEX M", ged)
        self.assertIn("2 DATE 12 JAN 1950", ged)
        self.assertIn("1 ALIA Marie Martin Durand", ged)
        self.assertIn("0 @F1@ FAM", ged)
        self.assertIn("1 HUSB @I1@", ged)
        self.assertIn("1 WIFE @I2@", ged)
        self.assertIn("2 DATE 14 JUL 1974", ged)
        self.assertIn("1 CHIL @I1@", ged)
        self.assertIn("2 TYPE Changement de nom", ged)
        self.assertIn("0 TRLR", ged)

    def test_export_view_staff_gets_attachment(self):
        admin = User.objects.create_superuser("admin3", password="secret123")
        self.client.force_login(admin)
        response = self.client.get(reverse("admin_export_gedcom"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("0 @I1@ INDI", response.content.decode())

    def test_export_view_non_staff_redirected(self):
        member = User.objects.create_user("member", password="secret123")
        self.client.force_login(member)
        response = self.client.get(reverse("admin_export_gedcom"))
        self.assertEqual(response.status_code, 302)

    def test_person_changelist_shows_export_button(self):
        admin = User.objects.create_superuser("admin4", password="secret123")
        self.client.force_login(admin)
        response = self.client.get(reverse("admin:genealogy_person_changelist"))
        self.assertContains(response, reverse("admin_export_gedcom"))
