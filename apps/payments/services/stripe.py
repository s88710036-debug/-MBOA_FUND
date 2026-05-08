"""
Service de paiement Stripe.

Ce module implémente l'intégration avec Stripe
pour les paiements par carte bancaire.

Documentation: https://stripe.com/docs

Stripe permet:
- Paiements par carte (Visa, Mastercard, etc.)
- Refunds complets ou partiels
- Webhooks pour confirmation
"""

import logging
import stripe
from decimal import Decimal
from typing import Dict, Any
from django.conf import settings
from django.utils import timezone

from .base import PaymentService, PaymentResponse

logger = logging.getLogger(__name__)


class StripePaymentService(PaymentService):
    """
    Service pour les paiements par carte avec Stripe.

    Stripe est un provider de paiement international
    supportant les cartes Visa, Mastercard, et autres.

    Attributes:
        api_key: Clé API Stripe

    Example:
        >>> service = StripePaymentService(is_sandbox=True)
        >>> response = service.create_payment(
        ...     amount=Decimal("50000"),
        ...     email="user@example.com",
        ...     reference="TONTINE-001"
        ... )
    """

    provider = "stripe"

    def __init__(self, is_sandbox: bool = True):
        """
        Initialise le service Stripe.

        Args:
            is_sandbox: Mode sandbox (True) ou production (False)
        """
        super().__init__(is_sandbox=is_sandbox)

        config = settings.STRIPE_SETTINGS
        self.secret_key = config.get("SECRET_KEY", "")
        self.public_key = config.get("PUBLIC_KEY", "")
        self.webhook_secret = config.get("WEBHOOK_SECRET", "")

        stripe.api_key = self.secret_key

        logger.info(f"StripePaymentService initialized: sandbox={is_sandbox}")

    def create_payment(
        self,
        amount: Decimal,
        phone: str,
        reference: str,
        user_id: int = None,
        metadata: Dict[str, Any] = None,
    ) -> PaymentResponse:
        """
        Crée une session de paiement Stripe Checkout.

        Args:
            amount: Montant du paiement en XOF (Stripe utilise les cents)
            phone: Numéro de téléphone (non utilisé par Stripe)
            reference: Référence unique de la transaction
            user_id: ID de l'utilisateur (optionnel)
            metadata: Métadonnées additionnelles (optionnel)

        Returns:
            PaymentResponse: Réponse avec l'URL de paiement Stripe
        """
        from apps.accounts.models import User
        from apps.payments.models import TransactionLog

        user_email = "customer@example.com"
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                user_email = user.email
            except User.DoesNotExist:
                pass

        if self.is_sandbox:
            return self._simulate_payment(amount, reference, user_id, user_email)

        user = user or User.objects.first()
        transaction = self._create_transaction_log(
            amount=amount, user=user, reference=reference
        )

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "xof",
                            "unit_amount": int(amount * 100),
                            "product_data": {
                                "name": f"Cotisation Tontine - {reference}",
                                "description": f"Paiement pour {reference}",
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{settings.STRIPE_SETTINGS.get('CALLBACK_URL', '')}success/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.STRIPE_SETTINGS.get('CALLBACK_URL', '')}cancel/",
                customer_email=user_email,
                metadata={
                    "transaction_id": transaction.transaction_id,
                    "reference": reference,
                },
            )

            transaction.external_transaction_id = checkout_session.id
            transaction.payment_url = checkout_session.url
            transaction.save()

            return PaymentResponse(
                success=True,
                transaction_id=transaction.transaction_id,
                payment_url=checkout_session.url,
                message="Session de paiement créée",
                data={
                    "checkout_session_id": checkout_session.id,
                    "public_key": self.public_key,
                },
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            transaction.mark_failed(error_message=str(e))

            return PaymentResponse(
                success=False,
                transaction_id=transaction.transaction_id,
                message=f"Erreur Stripe: {str(e)}",
                error_code=e.code,
            )

    def _simulate_payment(
        self, amount: Decimal, reference: str, user_id: int = None, email: str = None
    ) -> PaymentResponse:
        """
        Simule un paiement en mode sandbox.

        Args:
            amount: Montant du paiement
            reference: Référence de la transaction
            user_id: ID utilisateur
            email: Email du client

        Returns:
            PaymentResponse: Réponse simulée
        """
        from apps.accounts.models import User
        from apps.payments.models import TransactionLog

        user = User.objects.get(id=user_id) if user_id else User.objects.first()
        transaction = self._create_transaction_log(
            amount=amount, user=user, reference=reference
        )

        sandbox_session_id = f"SANDBOX_STRIPE_{uuid.uuid4().hex[:12].upper()}"
        transaction.external_transaction_id = sandbox_session_id
        transaction.save()

        logger.info(f"Sandbox Stripe payment created: {transaction.transaction_id}")

        return PaymentResponse(
            success=True,
            transaction_id=transaction.transaction_id,
            payment_url="",
            message="Paiement Stripe simulé (mode sandbox)",
            data={
                "sandbox": True,
                "sandbox_session_id": sandbox_session_id,
                "public_key": self.public_key,
            },
        )

    def check_payment_status(self, transaction_id: str) -> PaymentResponse:
        """
        Vérifie le statut d'un paiement Stripe.

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
                success=False, message=f"Transaction non trouvée: {transaction_id}"
            )

        if self.is_sandbox:
            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message="Mode sandbox",
                data={"status": transaction.status},
            )

        try:
            session = stripe.checkout.Session.retrieve(
                transaction.external_transaction_id
            )

            status = "pending"
            if session.payment_status == "paid":
                status = "success"
            elif session.payment_status == "unpaid":
                status = "failed"

            if status == "success":
                transaction.mark_success(response_data={"session": session})
            elif status == "failed":
                transaction.mark_failed(
                    error_message="Payment not completed",
                    response_data={"session": session},
                )

            return PaymentResponse(
                success=status == "success",
                transaction_id=transaction_id,
                message=f"Statut: {status}",
                data={"stripe_status": session.payment_status},
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe status check error: {e}")
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur: {str(e)}",
            )

    def handle_webhook(self, request_data: Dict[str, Any]) -> PaymentResponse:
        """
        Traite un webhook Stripe.

        Stripe envoie des webhooks pour:
        - checkout.session.completed
        - payment_intent.succeeded
        - payment_intent.payment_failed
        etc.

        Args:
            request_data: Données du webhook

        Returns:
            PaymentResponse: Réponse du traitement
        """
        from apps.payments.models import TransactionLog
        from apps.contributions.models import Contribution

        event_type = request_data.get("type")
        session = request_data.get("data", {}).get("object", {})

        transaction_id = session.get("metadata", {}).get("transaction_id")

        if not transaction_id:
            return PaymentResponse(
                success=False, message="transaction_id manquant dans les métadonnées"
            )

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
        except TransactionLog.DoesNotExist:
            return PaymentResponse(
                success=False, message=f"Transaction non trouvée: {transaction_id}"
            )

        if event_type == "checkout.session.completed":
            transaction.mark_success(response_data=request_data)

            if transaction.contribution:
                transaction.contribution.status = Contribution.Status.VALIDE
                transaction.contribution.validated_at = timezone.now()
                transaction.contribution.save()

            self._send_confirmation_email(transaction)

            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message="Paiement Stripe confirmé",
            )

        elif event_type == "checkout.session.expired":
            transaction.mark_failed(
                error_message="Session de paiement expirée", response_data=request_data
            )

            return PaymentResponse(
                success=False, transaction_id=transaction_id, message="Session expirée"
            )

        return PaymentResponse(
            success=True, transaction_id=transaction_id, message="Webhook traité"
        )

    def refund(self, transaction_id: str, amount: Decimal = None) -> PaymentResponse:
        """
        Effectue un remboursement Stripe.

        Args:
            transaction_id: ID de la transaction
            amount: Montant à rembourser (défaut: montant total)

        Returns:
            PaymentResponse: Réponse du remboursement
        """
        from apps.payments.models import TransactionLog

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
        except TransactionLog.DoesNotExist:
            return PaymentResponse(
                success=False, message=f"Transaction non trouvée: {transaction_id}"
            )

        if self.is_sandbox:
            transaction.status = TransactionLog.Status.REFUNDED
            transaction.completed_at = timezone.now()
            transaction.save()

            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message="Remboursement simulé",
            )

        try:
            session = stripe.checkout.Session.retrieve(
                transaction.external_transaction_id
            )
            payment_intent_id = session.payment_intent

            refund_params = {"payment_intent": payment_intent_id}
            if amount:
                refund_params["amount"] = int(amount * 100)

            refund = stripe.Refund.create(**refund_params)

            transaction.status = TransactionLog.Status.REFUNDED
            transaction.completed_at = timezone.now()
            transaction.save()

            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message=f"Remboursement effectué: {refund.id}",
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                message=f"Erreur: {str(e)}",
            )

    def _send_confirmation_email(self, transaction):
        """
        Envoie un email de confirmation.

        Args:
            transaction: L'objet TransactionLog
        """
        from django.core.mail import send_mail

        if not transaction.user or not transaction.user.email:
            return

        try:
            send_mail(
                subject=f"Paiement confirmé - TontineApp",
                message=(
                    f"Bonjour {transaction.user.get_full_name()},\n\n"
                    f"Votre paiement de {transaction.amount} XAF a été confirmé.\n"
                    f"Référence: {transaction.transaction_id}\n\n"
                    f"Merci pour votre confiance!"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[transaction.user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Error sending confirmation email: {e}")
