"""
Service de paiement Orange Money.

Ce module implémente l'intégration avec l'API Orange Money
pour les paiements mobile money en Afrique de l'Ouest.

Documentation: https://developer.orange.com

Providers supportés:
- Sénégal (XOF)
- Côte d'Ivoire (XOF)
- Mali (XOF)
- Burkina Faso (XOF)
- etc.

Retry automatique: 3 tentatives avec intervalle de 1h.
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


class OrangeMoneyService(PaymentService):
    """
    Service pour les paiements Orange Money.

    Ce service utilise l'API Orange Money Webpay pour:
    - Créer des demandes de paiement
    - Vérifier le statut des transactions
    - Traiter les webhooks de confirmation
    - Effectuer des remboursements

    Attributes:
        BASE_URL: URL de base de l'API Orange Money
        SANDBOX_URL: URL pour le mode sandbox

    Example:
        >>> service = OrangeMoneyService(is_sandbox=True)
        >>> response = service.create_payment(
        ...     amount=Decimal("50000"),
        ...     phone="+221771234567",
        ...     reference="TONTINE-001"
        ... )
        >>> if response.success:
        ...     print(f"Payment URL: {response.payment_url}")
    """

    provider = "orange_money"
    BASE_URL = "https://api.orange.com/orange-money-webpay"
    SANDBOX_URL = "https://api-sandbox.orange.com/orange-money-webpay"

    def __init__(self, is_sandbox: bool = True):
        """
        Initialise le service Orange Money.

        Args:
            is_sandbox: Mode sandbox (True) ou production (False)
        """
        super().__init__(is_sandbox=is_sandbox)

        config = settings.MOBILE_MONEY.get("ORANGE_MONEY", {})
        self.api_key = config.get("API_KEY", "")
        self.merchant_id = config.get("MERCHANT_ID", "")
        self.callback_url = config.get("CALLBACK_URL", "")

        self.base_url = self.SANDBOX_URL if is_sandbox else self.BASE_URL

        logger.info(
            f"OrangeMoneyService initialized: sandbox={is_sandbox}, "
            f"base_url={self.base_url}"
        )

    def _get_headers(self) -> Dict[str, str]:
        """
        Retourne les headers pour les requêtes API.

        Returns:
            Dict: Headers avec authentification
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
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
        Crée une demande de paiement Orange Money.

        Cette méthode initie un paiement en:
        1. Créant une transaction dans notre base
        2. Appelant l'API Orange Money pour obtenir une URL de paiement
        3. Retournant l'URL au client pour finaliser le paiement

        Args:
            amount: Montant du paiement en XOF
            phone: Numéro de téléphone du client (format international)
            reference: Référence unique de la transaction
            user_id: ID de l'utilisateur (optionnel)
            metadata: Métadonnées additionnelles (optionnel)

        Returns:
            PaymentResponse: Réponse avec l'URL de paiement
        """
        from apps.accounts.models import User
        from apps.payments.models import TransactionLog

        phone = self._normalize_phone(phone)

        # Mode sandbox: simulation
        if self.is_sandbox:
            return self._simulate_payment(amount, phone, reference, user_id)

        user = User.objects.get(id=user_id) if user_id else User.objects.first()
        transaction = self._create_transaction_log(
            amount=amount, user=user, reference=reference
        )

        try:
            order_id = f"ORD_{uuid.uuid4().hex[:12].upper()}"
            data = {
                "merchant_key": self.merchant_id,
                "order_id": order_id,
                "amount": str(amount),
                "currency": "XOF",
                "order_info": reference,
                "success_url": f"{self.callback_url}success/",
                "fail_url": f"{self.callback_url}fail/",
                "cancel_url": f"{self.callback_url}cancel/",
                "notif_url": self.callback_url,
                "payer_phone_number": phone,
            }

            logger.debug(f"Orange Money request: {data}")

            response = requests.post(
                f"{self.base_url}/v1/webpayment",
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )

            logger.debug(f"Orange Money response: {response.json()}")

            if response.status_code == 200:
                result = response.json()

                transaction.external_transaction_id = result.get(
                    "transaction_id", order_id
                )
                transaction.payment_url = result.get("payment_url", "")
                transaction.save()

                return PaymentResponse(
                    success=True,
                    transaction_id=transaction.transaction_id,
                    payment_url=result.get("payment_url", ""),
                    message="Demande de paiement créée avec succès",
                    data={
                        "order_id": order_id,
                        "external_id": result.get("transaction_id"),
                    },
                )
            else:
                error = response.json()
                transaction.mark_failed(
                    error_message=error.get("message", "Erreur inconnue"),
                    response_data=response.json(),
                )

                return PaymentResponse(
                    success=False,
                    transaction_id=transaction.transaction_id,
                    message=f"Erreur Orange Money: {error.get('message', 'Erreur inconnue')}",
                    error_code=error.get("error_code", str(response.status_code)),
                )

        except requests.RequestException as e:
            logger.error(f"Orange Money API error: {e}")
            transaction.mark_failed(error_message=str(e))

            # Planifier un retry
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

        Cette méthode retourne une réponse positive immédiate
        pour permettre de tester le flux sans appeler les APIs réels.

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

        sandbox_tx_id = f"SANDBOX_ORANGE_{uuid.uuid4().hex[:8].upper()}"
        transaction.external_transaction_id = sandbox_tx_id
        transaction.save()

        logger.info(f"Sandbox Orange payment created: {transaction.transaction_id}")

        return PaymentResponse(
            success=True,
            transaction_id=transaction.transaction_id,
            payment_url="",
            message="Paiement simulé avec succès (mode sandbox)",
            data={
                "sandbox": True,
                "sandbox_tx_id": sandbox_tx_id,
                "instructions": (
                    "Ce paiement est en mode test. "
                    "Utilisez l'endpoint /payments/sandbox/simulate-success/ "
                    "pour simuler une confirmation."
                ),
            },
        )

    def check_payment_status(self, transaction_id: str) -> PaymentResponse:
        """
        Vérifie le statut d'un paiement Orange Money.

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

        # Mode sandbox
        if self.is_sandbox:
            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message="Transaction en mode sandbox",
                data={"status": transaction.status, "sandbox": True},
            )

        try:
            external_id = transaction.external_transaction_id
            url = f"{self.base_url}/v1/status/{self.merchant_id}/{external_id}"

            response = requests.get(url, headers=self._get_headers(), timeout=30)

            if response.status_code == 200:
                result = response.json()
                status = self._map_orange_status(result.get("status"))

                if status == "success":
                    transaction.mark_success(response_data=result)
                elif status == "failed":
                    transaction.mark_failed(
                        error_message=result.get("error_message", "Échec inconnu"),
                        response_data=result,
                    )

                return PaymentResponse(
                    success=status == "success",
                    transaction_id=transaction_id,
                    message=f"Statut: {status}",
                    data={"orange_status": result},
                )

            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur API: {response.status_code}",
                error_code="API_ERROR",
            )

        except requests.RequestException as e:
            logger.error(f"Orange Money status check error: {e}")
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur de connexion: {str(e)}",
                error_code="CONNECTION_ERROR",
            )

    def handle_webhook(self, request_data: Dict[str, Any]) -> PaymentResponse:
        """
        Traite un webhook de notification Orange Money.

        Les webhooks sont envoyés par Orange lorsque:
        - Le paiement est confirmé
        - Le paiement est annulé
        - Une erreur survient

        Args:
            request_data: Données du webhook

        Returns:
            PaymentResponse: Réponse du traitement
        """
        from apps.payments.models import TransactionLog
        from apps.contributions.models import Contribution

        transaction_id = request_data.get("transaction_id")
        status = request_data.get("status")

        if not transaction_id:
            return PaymentResponse(
                success=False,
                message="transaction_id manquant dans le webhook",
                error_code="MISSING_FIELD",
            )

        try:
            transaction = TransactionLog.objects.get(
                external_transaction_id=transaction_id
            )
        except TransactionLog.DoesNotExist:
            return PaymentResponse(
                success=False,
                message=f"Transaction non trouvée: {transaction_id}",
                error_code="NOT_FOUND",
            )

        if status == "SUCCESS":
            transaction.mark_success(response_data=request_data)

            if transaction.contribution:
                transaction.contribution.status = Contribution.Status.VALIDE
                transaction.contribution.validated_at = timezone.now()
                transaction.contribution.save()

            self._send_confirmation_sms(transaction)

            return PaymentResponse(
                success=True,
                transaction_id=transaction.transaction_id,
                message="Paiement confirmé",
            )

        elif status in ["FAILURE", "CANCELLED"]:
            transaction.mark_failed(
                error_message=request_data.get(
                    "error_message", "Paiement annulé/échoué"
                ),
                response_data=request_data,
            )

            return PaymentResponse(
                success=False,
                transaction_id=transaction.transaction_id,
                message=f"Paiement {status.lower()}",
            )

        return PaymentResponse(
            success=True,
            transaction_id=transaction.transaction_id,
            message="Webhook traité",
        )

    def refund(self, transaction_id: str, amount: Decimal = None) -> PaymentResponse:
        """
        Effectue un remboursement Orange Money.

        Args:
            transaction_id: ID de la transaction à rembourser
            amount: Montant à rembourser (défaut: montant total)

        Returns:
            PaymentResponse: Réponse du remboursement
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

        if amount is None:
            amount = transaction.amount

        if self.is_sandbox:
            transaction.status = TransactionLog.Status.REFUNDED
            transaction.completed_at = timezone.now()
            transaction.save()

            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message="Remboursement simulé avec succès",
            )

        try:
            data = {
                "merchant_key": self.merchant_id,
                "transaction_id": transaction.external_transaction_id,
                "amount": str(amount),
                "currency": "XOF",
            }

            response = requests.post(
                f"{self.base_url}/v1/refund",
                json=data,
                headers=self._get_headers(),
                timeout=30,
            )

            if response.status_code == 200:
                transaction.status = TransactionLog.Status.REFUNDED
                transaction.completed_at = timezone.now()
                transaction.save()

                return PaymentResponse(
                    success=True,
                    transaction_id=transaction_id,
                    message="Remboursement effectué",
                )

            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur remboursement: {response.status_code}",
            )

        except requests.RequestException as e:
            logger.error(f"Orange Money refund error: {e}")
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur: {str(e)}",
                error_code="REFUND_ERROR",
            )

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalise un numéro de téléphone au format international.

        Args:
            phone: Numéro de téléphone

        Returns:
            str: Numéro normalisé
        """
        digits = "".join(filter(str.isdigit, phone))

        if digits.startswith("00"):
            digits = "+" + digits[2:]
        elif digits.startswith("0"):
            digits = "+221" + digits[1:]

        return digits

    def _map_orange_status(self, orange_status: str) -> str:
        """
        Convertit le statut Orange en notre format standard.

        Args:
            orange_status: Statut Orange Money

        Returns:
            str: Statut normalisé
        """
        status_map = {
            "SUCCESS": "success",
            "FAILURE": "failed",
            "CANCELLED": "cancelled",
            "PENDING": "pending",
            "PROCESSING": "processing",
        }

        return status_map.get(orange_status.upper(), "pending")

    def _send_confirmation_sms(self, transaction):
        """
        Envoie un SMS de confirmation après un paiement réussi.

        Args:
            transaction: L'objet TransactionLog
        """
        from .notification import SMSNotificationService

        if not transaction.user or not transaction.user.phone:
            return

        service = SMSNotificationService()

        message = (
            f"TontineApp: Paiement de {transaction.amount} XAF recu. "
            f"Transaction: {transaction.transaction_id}. Merci!"
        )

        service.send_sms(
            phone=str(transaction.user.phone),
            message=message,
            user=transaction.user,
            notification_type="payment_confirmation",
        )
