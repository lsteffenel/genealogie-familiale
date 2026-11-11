from django.core.management.base import BaseCommand

from genealogy.models import Event, Person, Union

MONTHS = [
    "", "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]


def gedcom_date(value):
    if not value:
        return ""
    return f"{value.day} {MONTHS[value.month]} {value.year}"


class Command(BaseCommand):
    help = "Exporte la base en fichier GEDCOM 5.5 (personnes, unions, événements)."

    def add_arguments(self, parser):
        parser.add_argument(
            "output",
            nargs="?",
            default="-",
            help="Fichier de sortie (défaut : stdout, '-' pour stdout)",
        )

    def handle(self, *args, **options):
        content = self.build()
        if options["output"] == "-":
            self.stdout.write(content)
        else:
            with open(options["output"], "w", encoding="utf-8") as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS(f"Export GEDCOM écrit dans {options['output']}"))

    def build(self):
        import io

        out = io.StringIO()
        self.write(out)
        return out.getvalue()

    def write(self, out):
        w = out.write
        w("0 HEAD\n1 VERS 5.5.5\n1 GEDC\n2 VERS 5.5.5\n2 FORM LINEAGE-LINKED\n1 CHAR UTF-8\n")
        persons = list(Person.objects.all())
        by_pk = {p.pk: p for p in persons}
        for person in persons:
            xref = person.gedcom_id or f"I{person.pk}"
            w(f"0 @{xref}@ INDI\n")
            maiden = f" {person.maiden_name}" if person.maiden_name else ""
            w(f"1 NAME {person.first_name} /{person.last_name}/{maiden}\n")
            if person.maiden_name:
                w(f"1 ALIA {person.first_name} {person.last_name} {person.maiden_name}\n")
            if person.gender in ("M", "F"):
                w(f"1 SEX {person.gender}\n")
            if person.birth_date or person.birth_place:
                w("1 BIRT\n")
                if person.birth_date:
                    w(f"2 DATE {gedcom_date(person.birth_date)}\n")
                if person.birth_place:
                    w(f"2 PLAC {person.birth_place}\n")
            if person.death_date or person.death_place:
                w("1 DEAT\n")
                if person.death_date:
                    w(f"2 DATE {gedcom_date(person.death_date)}\n")
                if person.death_place:
                    w(f"2 PLAC {person.death_place}\n")
            if person.biography:
                w(f"1 NOTE {person.biography}\n")
            for event in person.events.all():
                w("1 EVEN\n")
                w(f"2 TYPE {event.get_event_type_display()}\n")
                w(f"2 TITL {event.title}\n")
                if event.date:
                    w(f"2 DATE {gedcom_date(event.date)}\n")
                if event.place:
                    w(f"2 PLAC {event.place}\n")
                if event.description:
                    w(f"2 NOTE {event.description}\n")
        for union in Union.objects.prefetch_related("children", "partner_a", "partner_b"):
            xref = union.gedcom_id or f"F{union.pk}"
            w(f"0 @{xref}@ FAM\n")
            w(f"1 HUSB @{by_pk[union.partner_a_id].gedcom_id or f'I{union.partner_a_id}'}@\n")
            w(f"1 WIFE @{by_pk[union.partner_b_id].gedcom_id or f'I{union.partner_b_id}'}@\n")
            if union.date or union.place:
                w("1 MARR\n")
                if union.date:
                    w(f"2 DATE {gedcom_date(union.date)}\n")
                if union.place:
                    w(f"2 PLAC {union.place}\n")
            for child in union.children.all():
                w(f"1 CHIL @{child.gedcom_id or f'I{child.pk}'}@\n")
        w("0 TRLR\n")
