import re
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from genealogy.models import Person, Union

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def parse_gedcom_date(raw):
    raw = raw.strip()
    for prefix in ("ABT ", "EST ", "CAL ", "BEF ", "AFT ", "FROM ", "TO "):
        if raw.upper().startswith(prefix):
            raw = raw[len(prefix):]
    parts = raw.split()
    if len(parts) == 3 and parts[1].upper() in MONTHS:
        try:
            return date(int(parts[2]), MONTHS[parts[1].upper()], int(parts[0]))
        except ValueError:
            return None
    if len(parts) == 1 and parts[0].isdigit() and len(parts[0]) == 4:
        return date(int(parts[0]), 1, 1)
    return None


def parse_name(value):
    value = value.strip()
    parts = value.split("/")
    first = parts[0].strip()
    last = parts[1].strip() if len(parts) > 1 else ""
    maiden = parts[2].strip() if len(parts) > 2 else ""
    return first, last, maiden


def tokenize(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    records = []
    current = None
    for line in lines:
        if not line.strip():
            continue
        match = re.match(r"^(\d+)\s+(@[^@]+@\s+)?(\w+)(?:\s+(.*))?$", line)
        if not match:
            continue
        level, xref, tag, rest = match.groups()
        level = int(level)
        entry = {"level": level, "xref": (xref or "").strip("@ "), "tag": tag.upper(), "rest": (rest or "").strip()}
        if level == 0:
            if current is not None:
                records.append(current)
            current = [entry]
        elif current is not None:
            current.append(entry)
    if current is not None:
        records.append(current)
    return records


def sub_entries(record, tag):
    return [e for e in record if e["level"] == record[0]["level"] + 1 and e["tag"] == tag]


def sub_value(record, tag):
    entries = sub_entries(record, tag)
    return entries[0]["rest"] if entries else ""


def sub_sub_value(record, tag, sub_tag):
    base_level = record[0]["level"]
    for i, entry in enumerate(record):
        if entry["level"] == base_level + 1 and entry["tag"] == tag:
            for sub in record[i + 1:]:
                if sub["level"] <= base_level + 1:
                    break
                if sub["level"] == base_level + 2 and sub["tag"] == sub_tag:
                    return sub["rest"]
    return ""


class Command(BaseCommand):
    help = "Importe un fichier GEDCOM (export Geneanet) : personnes, unions et enfants."

    def add_arguments(self, parser):
        parser.add_argument("gedcom_file", help="Chemin vers le fichier .ged")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Analyse le fichier sans écrire en base",
        )

    def handle(self, *args, **options):
        path = options["gedcom_file"]
        dry_run = options["dry_run"]
        records = tokenize(path)

        individuals = [r for r in records if r[0]["tag"] == "INDI"]
        families = [r for r in records if r[0]["tag"] == "FAM"]

        self.stdout.write(f"{len(individuals)} individu(s), {len(families)} famille(s) détecté(s).")

        def build():
            persons = {}
            for record in individuals:
                xref = record[0]["xref"]
                first, last, maiden = parse_name(sub_value(record, "NAME"))
                if not last:
                    last = first
                    first = ""
                gender = sub_value(record, "SEX").upper()[:1]
                if gender not in ("M", "F"):
                    gender = ""
                birth = next((e for e in sub_entries(record, "BIRT")), None)
                death = next((e for e in sub_entries(record, "DEAT")), None)
                person = Person(
                    first_name=first,
                    last_name=last,
                    maiden_name=maiden,
                    gender=gender,
                    birth_date=parse_gedcom_date(sub_sub_value(record, "BIRT", "DATE")) if birth else None,
                    birth_place=sub_sub_value(record, "BIRT", "PLAC") if birth else "",
                    death_date=parse_gedcom_date(sub_sub_value(record, "DEAT", "DATE")) if death else None,
                    death_place=sub_sub_value(record, "DEAT", "PLAC") if death else "",
                    gedcom_id=xref or None,
                )
                persons[xref] = person

            unions = {}
            for record in families:
                xref = record[0]["xref"]
                husb = sub_value(record, "HUSB").strip("@")
                wife = sub_value(record, "WIFE").strip("@")
                partner_a = persons.get(husb)
                partner_b = persons.get(wife)
                if not partner_a or not partner_b:
                    continue
                marriage = next((e for e in sub_entries(record, "MARR")), None)
                union = Union(
                    partner_a=partner_a,
                    partner_b=partner_b,
                    date=parse_gedcom_date(sub_sub_value(record, "MARR", "DATE")) if marriage else None,
                    place=sub_sub_value(record, "MARR", "PLAC") if marriage else "",
                    gedcom_id=xref or None,
                )
                unions[xref] = (union, [c.strip("@") for c in
                                        [e["rest"] for e in sub_entries(record, "CHIL")]])

            if not dry_run:
                with transaction.atomic():
                    for person in persons.values():
                        person.save()
                    for union, child_xrefs in unions.values():
                        union.save()
                        union.children.set([persons[c] for c in child_xrefs if c in persons])
            return persons, unions

        persons, unions = build()

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run : aucune écriture en base."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Import terminé : {len(persons)} personne(s), {len(unions)} union(s)."
            ))
