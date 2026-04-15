from django import forms
from .models import Draw, DrawWinner


class DrawForm(forms.ModelForm):
    class Meta:
        model = Draw
        fields = ("name", "selection_method", "scheduled_date", "winner_count", "notes")
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom du tirage"}
            ),
            "selection_method": forms.Select(attrs={"class": "form-select"}),
       
            "scheduled_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "winner_count": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.cycle = kwargs.pop("cycle", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.cycle:
            cleaned_data["cycle"] = self.cycle
            cleaned_data["tontine"] = self.cycle.tontine
            cleaned_data["number"] = self.cycle.draws.count() + 1
            cleaned_data["total_pot"] = self.cycle.total_amount
            cleaned_data["prize_amount"] = self.cycle.total_amount
            cleaned_data["created_by"] = self.initial.get("created_by")
        return cleaned_data


class DrawWinnerForm(forms.ModelForm):
    class Meta:
        model = DrawWinner
        fields = ("status", "payout_reference", "notes")
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "payout_reference": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Référence du paiement"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
