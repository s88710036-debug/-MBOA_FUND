from django import forms
from django.core.exceptions import ValidationError
from .models import Tontine, TontineMembership, Cycle


class TontineForm(forms.ModelForm):
    class Meta:
        model = Tontine
        fields = (
            "name",
            "description",
            "frequency",
            "amount_per_member",
            "max_members",
            "min_members",
            "start_date",
            "end_date",
            "is_public",
            "image",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom de la tontine"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Description de la tontine",
                }
            ),
            "frequency": forms.Select(attrs={"class": "form-select"}),
            "amount_per_member": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Montant par membre"}
            ),
            "max_members": forms.NumberInput(attrs={"class": "form-control"}),
            "min_members": forms.NumberInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        max_members = cleaned_data.get("max_members")
        min_members = cleaned_data.get("min_members")
        amount = cleaned_data.get("amount_per_member")

        if min_members and max_members and min_members > max_members:
            raise ValidationError(
                "Le nombre minimum de membres ne peut pas être supérieur au maximum."
            )

        if amount and amount <= 0:
            raise ValidationError("Le montant doit être supérieur à zéro.")

        return cleaned_data


class JoinTontineForm(forms.Form):
    invite_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Code d'invitation",
                "autocomplete": "off",
            }
        ),
    )

    def clean_invite_code(self):
        code = self.cleaned_data.get("invite_code").upper()
        try:
            tontine = Tontine.objects.get(invite_code=code)
        except Tontine.DoesNotExist:
            raise ValidationError("Code d'invitation invalide.")
        return code


class CycleForm(forms.ModelForm):
    class Meta:
        model = Cycle
        fields = ("name", "start_date", "end_date", "amount_per_member")
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du cycle (ex: Tour 1 - Janvier)",
                }
            ),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "amount_per_member": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.tontine = kwargs.pop("tontine", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.tontine:
            cleaned_data["tontine"] = self.tontine
            cleaned_data["number"] = self.tontine.cycles.count() + 1
        return cleaned_data


class MembershipActionForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            ("approve", "Approuver"),
            ("suspend", "Suspendre"),
            ("reactivate", "Réactiver"),
            ("remove", "Retirer"),
        ]
    )
    membership_id = forms.IntegerField(widget=forms.HiddenInput())


class TontineSettingsForm(forms.ModelForm):
    class Meta:
        model = Tontine
        fields = (
            "name",
            "description",
            "frequency",
            "amount_per_member",
            "max_members",
            "min_members",
            "start_date",
            "end_date",
            "is_public",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "frequency": forms.Select(attrs={"class": "form-select"}),
            "amount_per_member": forms.NumberInput(attrs={"class": "form-control"}),
            "max_members": forms.NumberInput(attrs={"class": "form-control"}),
            "min_members": forms.NumberInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
