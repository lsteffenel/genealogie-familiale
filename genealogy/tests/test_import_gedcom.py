import os
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from genealogy.models import Person, Union

SAMPLE = os.path.join(os.path.dirname(__file__), "sample.ged")


class ImportGedcomTests(TestCase):
    def test_import_creates_persons_union_and_child_link(self):
        out = StringIO()
        call_command("import_gedcom", SAMPLE, stdout=out)

        self.assertEqual(Person.objects.count(), 3)
        jean = Person.objects.get(gedcom_id="I1")
        self.assertEqual(jean.first_name, "Jean")
        self.assertEqual(jean.last_name, "Dupont")
        self.assertEqual(str(jean.birth_date), "1950-01-12")
        self.assertEqual(jean.birth_place, "Paris, France")
        self.assertEqual(str(jean.death_date), "2010-03-03")
        self.assertEqual(jean.gender, "M")

        marie = Person.objects.get(gedcom_id="I2")
        self.assertEqual(marie.maiden_name, "Durand")

        self.assertEqual(Union.objects.count(), 1)
        union = Union.objects.get(gedcom_id="F1")
        self.assertEqual({union.partner_a, union.partner_b}, {jean, marie})
        self.assertEqual(str(union.date), "1974-07-14")
        self.assertEqual(list(union.children.all()), [Person.objects.get(gedcom_id="I3")])

    def test_dry_run_writes_nothing(self):
        out = StringIO()
        call_command("import_gedcom", SAMPLE, "--dry-run", stdout=out)
        self.assertEqual(Person.objects.count(), 0)
        self.assertEqual(Union.objects.count(), 0)

    def test_import_name_change_events(self):
        import tempfile

        from genealogy.models import Event

        ged = """0 HEAD
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Louis /Steffenel/
1 SEX M
1 BIRT
2 DATE 1961
1 NAME Louis /Estefanel/
1 ALIA Louis Estefanel
2 NOTE Graphie d'origine
1 EVEN
2 TYPE Changement de nom
2 DATE 1961
2 PLAC Rome, Italie
2 NOTE Naturalisation italienne
0 TRLR
"""
        with tempfile.NamedTemporaryFile("w", suffix=".ged", delete=False) as f:
            f.write(ged)
            path = f.name
        call_command("import_gedcom", path)
        person = Person.objects.get(gedcom_id="I1")
        self.assertEqual(person.last_name, "Steffenel")
        events = list(person.events.all())
        self.assertEqual(len(events), 3)
        self.assertTrue(all(e.event_type == Event.EventType.NAME_CHANGE for e in events))
        even = next(e for e in events if e.title == "Changement de nom")
        self.assertEqual(str(even.date), "1961-01-01")
        self.assertEqual(even.place, "Rome, Italie")
        self.assertIn("Naturalisation italienne", even.description)
        alia = next(e for e in events if e.title == "Louis Estefanel" and e.description)
        self.assertEqual(alia.description, "Graphie d'origine")
        self.assertTrue(any(e.title == "Louis Estefanel" and not e.description for e in events))
