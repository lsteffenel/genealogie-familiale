from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Event, Person, Union


class MediaProposalForm(forms.Form):
    person = forms.ModelChoiceField(queryset=Person.objects.all(), label=_("Personne associée"))
    title = forms.CharField(max_length=255, label=_("Titre de la photo"))
    description = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}), label=_("Description")
    )
    image = forms.ImageField(label=_("Fichier photo"))
    note = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Commentaire (affiché au modérateur)"),
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("image"):
            raise forms.ValidationError(_("Indiquez un fichier à uploader."))
        return cleaned


class PersonProposalForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "first_name", "last_name", "maiden_name", "gender",
            "birth_date", "birth_place", "death_date", "death_place",
            "biography",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "death_date": forms.DateInput(attrs={"type": "date"}),
            "biography": forms.Textarea(attrs={"rows": 5}),
        }

    def changed_fields(self, original):
        changes = {}
        for field in self.cleaned_data:
            new_value = self.cleaned_data[field]
            old_value = getattr(original, field)
            if hasattr(old_value, "isoformat"):
                old_value = old_value.isoformat() if old_value else None
            if new_value in (None, "") and old_value in (None, ""):
                continue
            if str(old_value or "") != str(new_value or ""):
                if hasattr(new_value, "isoformat"):
                    new_value = new_value.isoformat()
                changes[field] = new_value if new_value not in (None, "") else ""
        return changes


class ProposalNoteForm(forms.Form):
    note = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Commentaire (affiché au modérateur)"),
    )


class ReviewForm(forms.Form):
    comment = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        label=_("Commentaire de modération"),
    )


class EventProposalForm(forms.Form):
    event_type = forms.ChoiceField(
        choices=Event.EventType.choices, required=False, label=_("Type d'événement")
    )
    title = forms.CharField(required=False, max_length=255, label=_("Titre"))
    date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}), label=_("Date")
    )
    place = forms.CharField(required=False, max_length=255, label=_("Lieu"))
    description = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}), label=_("Description")
    )

    def is_filled(self):
        return any(
            self.data.get(name) for name in ("event_type", "title", "date", "place", "description")
        )


class UnionProposalForm(forms.Form):
    partner = forms.ModelChoiceField(
        queryset=Person.objects.all(), required=False, label=_("Partenaire")
    )
    union_type = forms.ChoiceField(
        choices=Union.UnionType.choices, required=False, label=_("Type d'union")
    )
    date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}), label=_("Date")
    )
    place = forms.CharField(required=False, max_length=255, label=_("Lieu"))
    notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}), label=_("Notes")
    )

    def is_filled(self):
        return any(
            self.data.get(name) for name in ("partner", "union_type", "date", "place", "notes")
        )
