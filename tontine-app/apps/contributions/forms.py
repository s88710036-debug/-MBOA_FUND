from django import forms
from django.core.exceptions import ValidationError
from .models import Contribution, PaymentRequest


class ContributionForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = (
            "amount",
            "payment_method",
            "sender_name",
            "sender_phone",
            "reference_number",
            "proof_document",
            "notes",
        )
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Montant en XOF"}
            ),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "sender_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom de l'expéditeur"}
            ),
            "sender_phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Numéro expéditeur"}
            ),
            "reference_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Numéro de transaction (optionnel)",
                }
            ),
            "proof_document": forms.FileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Notes additionnelles",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.cycle = kwargs.pop("cycle", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if self.cycle and self.user:
            existing = Contribution.objects.filter(
                user=self.user, cycle=self.cycle
            ).exists()
            if existing:
                raise ValidationError(
                    "Vous avez déjà soumis une cotisation pour ce cycle."
                )

            amount = cleaned_data.get("amount")
            if amount and amount != self.cycle.amount_per_member:
                if amount < self.cycle.amount_per_member:
                    raise ValidationError(
                        f"Le montant minimum est {self.cycle.amount_per_member} XAF."
                    )

        return cleaned_data


class ManualContributionForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = (
            "user",
            "amount",
            "payment_method",
            "sender_name",
            "sender_phone",
            "reference_number",
            "notes",
        )
        widgets = {
            "user": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "sender_name": forms.TextInput(attrs={"class": "form-control"}),
            "sender_phone": forms.TextInput(attrs={"class": "form-control"}),
            "reference_number": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class ContributionValidationForm(forms.Form):
    contribution_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ("validate", "Valider la cotisation"),
            ("reject", "Rejeter la cotisation"),
        ]
    )
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        required=False,
    )


class PaymentRequestForm(forms.ModelForm):
    class Meta:
        model = PaymentRequest
        fields = ("payment_method",)
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-select"}),
        }


class BulkValidationForm(forms.Form):
    contribution_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=[
            ("validate_all", "Valider toutes les cotisations sélectionnées"),
            ("reject_all", "Rejeter toutes les cotisations sélectionnées"),
        ]
    )
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        required=False,
    )
