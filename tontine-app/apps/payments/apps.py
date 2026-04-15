"""
Configuration de l'application payments.
"""

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """
    Configuration de l'application de paiement.

    Cette application gère:
    - Les transactions via Orange Money
    - Les transactions via Wave
    - Les transactions par carte (Stripe)
    - Les notifications SMS
    - Le retry automatique des paiements échoués
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    verbose_name = "Paiements"

    def ready(self):
        """
        Initialisation au démarrage de l'application.
        """
        pass
