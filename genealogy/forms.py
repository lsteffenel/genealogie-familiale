from django import forms

from .models import Person


class MediaProposalForm(forms.Form):
    person = forms.ModelChoiceField(queryset=Person.objects.all(), label="Personne associée")
    title = forms.CharField(max_length=255, label="Titre de la photo")
    description = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Description"
    )
    image = forms.ImageField(required=False, label="Fichier photo (stockage local)")
    google_photo_media_item_id = forms.CharField(
        required=False, max_length=255,
        label="Identifiant Google Photos (si la photo vient de l'album partagé)",
    )
    note = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        label="Commentaire (affiché au modérateur)",
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("image") and not cleaned.get("google_photo_media_item_id"):
            raise forms.ValidationError(
                "Indiquez un fichier à uploader ou un identifiant Google Photos."
            )
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
        label="Commentaire (affiché au modérateur)",
    )


class ReviewForm(forms.Form):
    comment = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        label="Commentaire de modération",
    )
