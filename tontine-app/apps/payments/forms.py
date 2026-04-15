"""
Formulaires pour les paiements.
"""

from django import forms
from django.core.exceptions import ValidationError


class PaymentMethodForm(forms.Form):
    """
    Formulaire pour la sélection de la méthode de paiement.

    Attributes:
        payment_method: Méthode choisie (orange_money, wave, stripe)
        phone_number: Numéro de téléphone pour Mobile Money
    """

    payment_method = forms.ChoiceField(
        label="Mode de paiement",
        choices=[
            ("orange_money", "Orange Money"),
            ("wave", "Wave"),
            ("stripe", "Carte bancaire (Stripe)"),
        ],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="orange_money",
    )

    phone_number = forms.CharField(
        label="Numéro de téléphone",
        max_length=20,
        required=False,
        help_text="Requis pour Mobile Money (Orange Money, Wave)",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+221 XX XXX XX XX",
            }
        ),
    )

    def clean(self):
        """
        Valide le formulaire.

        Si Mobile Money est sélectionné, le numéro de téléphone
        devient obligatoire.
        """
        cleaned_data = super().clean()

        payment_method = cleaned_data.get("payment_method")
        phone_number = cleaned_data.get("phone_number")

        if payment_method in ["orange_money", "wave"] and not phone_number:
            raise ValidationError(
                "Le numéro de téléphone est requis pour Mobile Money."
            )

        if phone_number:
            digits = "".join(filter(str.isdigit, phone_number))
            if len(digits) < 8:
                raise ValidationError("Le numéro de téléphone semble invalide.")

        return cleaned_data


class PaymentSimulationForm(forms.Form):
    """
    Formulaire pour simuler un paiement en mode sandbox.

    Ce formulaire permet de tester le flux de paiement
    sans appeler les APIs réels.
    """

    simulate_result = forms.ChoiceField(
        label="Résultat simulé",
        choices=[
            ("success", "Succès"),
            ("failure", "Échec"),
        ],
        widget=forms.RadioSelect(),
        initial="success",
    )
