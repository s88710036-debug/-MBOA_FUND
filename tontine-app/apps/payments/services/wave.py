"""
Service de paiement Wave.

Ce module implémente l'intégration avec l'API Wave
pour les paiements mobile money au Sénégal.

Documentation: https://developers.wave.com

Note: Wave est actuellement disponible uniquement au Sénégal.
"""

import logging
import requests
import uuid
from decimal import Decimal
from typing import Dict, Any
from django.conf import settings
from django.utils import timezone

from .base import PaymentService, PaymentResponse

logger = logging.getLogger(__name__)


class WaveService(PaymentService):
    """
    Service pour les paiements Wave.

    Wave est un provider de paiement mobile money
    principalement utilisé au Sénégal.

    Attributes:
        BASE_URL: URL de base de l'API Wave
        SANDBOX_URL: URL pour le mode sandbox

    Example:
        >>> service = WaveService(is_sandbox=True)
        >>> response = service.create_payment(
        ...     amount=Decimal("50000"),
        ...     phone="+221771234567",
        ...     reference="TONTINE-001"
        ... )
    """

    provider = "wave"
    BASE_URL = "https://api.wave.com/v1"

    def __init__(self, is_sandbox: bool = True):
        """
        Initialise le service Wave.

        Args:
            is_sandbox: Mode sandbox (True) ou production (False)
        """
        super().__init__(is_sandbox=is_sandbox)

        config = settings.MOBILE_MONEY.get("WAVE", {})
        self.api_key = config.get("API_KEY", "")
        self.api_secret = config.get("API_SECRET", "")
        self.callback_url = config.get("CALLBACK_URL", "")

        logger.info(f"WaveService initialized: sandbox={is_sandbox}")

    def _get_headers(self) -> Dict[str, str]:
        """
        Retourne les headers pour les requêtes API.

        Returns:
            Dict: Headers avec authentification
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "WAVE-API-Version": "2023-01-01",
        }

    def create_payment(
        self,
        amount: Decimal,
        phone: str,
        reference: str,
        user_id: int = None,
        metadata: Dict[str, Any] = None,
    ) -> PaymentResponse:
        """
        Crée une demande de paiement Wave.

        Args:
            amount: Montant du paiement en XOF
            phone: Numéro de téléphone du client
            reference: Référence unique de la transaction
            user_id: ID de l'utilisateur (optionnel)
            metadata: Métadonnées additionnelles (optionnel)

        Returns:
            PaymentResponse: Réponse avec l'URL de paiement
        """
        from apps.accounts.models import User
        from apps.payments.models import TransactionLog

        phone = self._normalize_phone(phone)

        if self.is_sandbox:
            return self._simulate_payment(amount, phone, reference, user_id)

        user = User.objects.get(id=user_id) if user_id else User.objects.first()
        transaction = self._create_transaction_log(
            amount=amount, user=user, reference=reference
        )

        try:
            data = {
                "amount": str(amount),
                "currency": "XOF",
                "error_url": f"{self.callback_url}error/",
                "success_url": f"{self.callback_url}success/",
                "cancel_url": f"{self.callback_url}cancel/",
                "client_reference_id": transaction.transaction_id,
                "merchant_reference_id": reference,
                "phone_number": phone,
            }

            logger.debug(f"Wave request: {data}")

            response = requests.post(
                f"{self.BASE_URL}/checkouts",
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )

            logger.debug(f"Wave response: {response.json()}")

            if response.status_code in [200, 201]:
                result = response.json()

                transaction.external_transaction_id = result.get("id")
                transaction.payment_url = result.get("redirect_url", "")
                transaction.save()

                return PaymentResponse(
                    success=True,
                    transaction_id=transaction.transaction_id,
                    payment_url=result.get("redirect_url", ""),
                    message="Demande de paiement créée",
                    data={"wave_checkout_id": result.get("id")},
                )

            error = response.json()
            transaction.mark_failed(
                error_message=error.get("message", "Erreur inconnue"),
                response_data=error,
            )

            return PaymentResponse(
                success=False,
                transaction_id=transaction.transaction_id,
                message=f"Erreur Wave: {error.get('message', 'Erreur inconnue')}",
                error_code=str(response.status_code),
            )

        except requests.RequestException as e:
            logger.error(f"Wave API error: {e}")
            transaction.mark_failed(error_message=str(e))
            self._schedule_retry(transaction.transaction_id, 1)

            return PaymentResponse(
                success=False,
                transaction_id=transaction.transaction_id,
                message=f"Erreur de connexion: {str(e)}",
                error_code="CONNECTION_ERROR",
            )

    def _simulate_payment(
        self, amount: Decimal, phone: str, reference: str, user_id: int = None
    ) -> PaymentResponse:
        """
        Simule un paiement en mode sandbox.

        Args:
            amount: Montant du paiement
            phone: Numéro de téléphone
            reference: Référence de la transaction
            user_id: ID utilisateur

        Returns:
            PaymentResponse: Réponse simulée
        """
        from apps.accounts.models import User
        from apps.payments.models import TransactionLog

        user = User.objects.get(id=user_id) if user_id else User.objects.first()
        transaction = self._create_transaction_log(
            amount=amount, user=user, reference=reference
        )

        sandbox_tx_id = f"SANDBOX_WAVE_{uuid.uuid4().hex[:8].upper()}"
        transaction.external_transaction_id = sandbox_tx_id
        transaction.save()

        logger.info(f"Sandbox Wave payment created: {transaction.transaction_id}")

        return PaymentResponse(
            success=True,
            transaction_id=transaction.transaction_id,
            payment_url="",
            message="Paiement Wave simulé (mode sandbox)",
            data={
                "sandbox": True,
                "sandbox_tx_id": sandbox_tx_id,
            },
        )

    def check_payment_status(self, transaction_id: str) -> PaymentResponse:
        """
        Vérifie le statut d'un paiement Wave.

        Args:
            transaction_id: ID de notre transaction

        Returns:
            PaymentResponse: Réponse avec le statut actuel
        """
        from apps.payments.models import TransactionLog

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
        except TransactionLog.DoesNotExist:
            return PaymentResponse(
                success=False,
                message=f"Transaction non trouvée: {transaction_id}",
                error_code="NOT_FOUND",
            )

        if self.is_sandbox:
            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message="Mode sandbox",
                data={"status": transaction.status},
            )

        try:
            checkout_id = transaction.external_transaction_id
            url = f"{self.BASE_URL}/checkouts/{checkout_id}"

            response = requests.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code == 200:
                result = response.json()
                status = self._map_wave_status(result.get("status"))

                if status == "success":
                    transaction.mark_success(response_data=result)
                elif status == "failed":
                    transaction.mark_failed(
                        error_message=result.get("error_message", "Échec"),
                        response_data=result,
                    )

                return PaymentResponse(
                    success=status == "success",
                    transaction_id=transaction_id,
                    message=f"Statut: {status}",
                    data={"wave_status": result},
                )

            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur API: {response.status_code}",
            )

        except requests.RequestException as e:
            logger.error(f"Wave status check error: {e}")
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur: {str(e)}",
            )

    def handle_webhook(self, request_data: Dict[str, Any]) -> PaymentResponse:
        """
        Traite un webhook Wave.

        Args:
            request_data: Données du webhook

        Returns:
            PaymentResponse: Réponse du traitement
        """
        from apps.payments.models import TransactionLog
        from apps.contributions.models import Contribution

        event_type = request_data.get("event")
        checkout_id = request_data.get("checkout_id")

        try:
            transaction = TransactionLog.objects.get(
                external_transaction_id=checkout_id
            )
        except TransactionLog.DoesNotExist:
            return PaymentResponse(
                success=False, message=f"Transaction non trouvée: {checkout_id}"
            )

        if event_type == "CHECKOUT_COMPLETED":
            transaction.mark_success(response_data=request_data)

            if transaction.contribution:
                transaction.contribution.status = Contribution.Status.VALIDE
                transaction.contribution.validated_at = timezone.now()
                transaction.contribution.save()

            self._send_confirmation_sms(transaction)

            return PaymentResponse(
                success=True,
                transaction_id=transaction.transaction_id,
                message="Paiement Wave confirmé",
            )

        return PaymentResponse(
            success=True,
            transaction_id=transaction.transaction_id,
            message="Webhook traité",
        )

    def refund(self, transaction_id: str, amount: Decimal = None) -> PaymentResponse:
        """
        Effectue un remboursement Wave.

        Note: Wave ne supporte pas les remboursements.

        Args:
            transaction_id: ID de la transaction
            amount: Montant à rembourser

        Returns:
            PaymentResponse: Réponse du remboursement
        """
        return PaymentResponse(
            success=False,
            message="Les remboursements ne sont pas supportés par Wave",
            error_code="NOT_SUPPORTED",
        )

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalise un numéro de téléphone.

        Args:
            phone: Numéro de téléphone

        Returns:
            str: Numéro normalisé
        """
        digits = "".join(filter(str.isdigit, phone))

        if digits.startswith("00"):
            return "+" + digits[2:]
        elif digits.startswith("0"):
            return "+221" + digits[1:]

        return phone

    def _map_wave_status(self, wave_status: str) -> str:
        """
        Convertit le statut Wave en format standard.

        Args:
            wave_status: Statut Wave

        Returns:
            str: Statut normalisé
        """
        status_map = {
            "COMPLETED": "success",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "PENDING": "pending",
        }

        return status_map.get(wave_status.upper(), "pending")

    def _send_confirmation_sms(self, transaction):
        """
        Envoie un SMS de confirmation.

        Args:
            transaction: L'objet TransactionLog
        """
        from .notification import SMSNotificationService

        if not transaction.user or not transaction.user.phone:
            return

        service = SMSNotificationService()

        message = f"TontineApp: Paiement Wave de {transaction.amount} XAF recu. Merci!"

        service.send_sms(
            phone=str(transaction.user.phone),
            message=message,
            user=transaction.user,
            notification_type="payment_confirmation",
        )
