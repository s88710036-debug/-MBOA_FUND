"""
Classe de base abstraite pour les services de paiement.

Ce module définit l'interface commune à tous les providers
et implémente les fonctionnalités communes comme le retry
automatique et le logging.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class PaymentResponse:
    """
    Réponse standardisée pour toutes les opérations de paiement.

    Attributes:
        success: Indique si l'opération a réussi
        transaction_id: ID de la transaction (optionnel)
        payment_url: URL de redirection vers le provider (optionnel)
        message: Message descriptif
        error_code: Code d'erreur (optionnel)
        data: Données supplémentaires (optionnel)
    """

    success: bool
    message: str
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    error_code: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        """Convertit la réponse en dictionnaire."""
        return {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "payment_url": self.payment_url,
            "message": self.message,
            "error_code": self.error_code,
            "data": self.data,
        }


class PaymentService(ABC):
    """
    Classe abstraite pour les services de paiement.

    Cette classe définit l'interface commune à tous les providers
    et implémente les fonctionnalités communes:
    - Logging des transactions
    - Retry automatique
    - Gestion des erreurs

    Attributes:
        provider: Nom du provider de paiement
        is_sandbox: Mode sandbox si True
        max_retries: Nombre maximum de tentatives de retry
        retry_interval: Intervalle entre les retries (en secondes)

    Retry Strategy:
    - 3 tentatives maximum
    - Intervalle: 1h entre chaque tentative
    - Log de chaque tentative
    """

    provider: str = "base"
    MAX_RETRIES: int = 3
    RETRY_INTERVAL: int = 3600  # 1 heure

    def __init__(self, is_sandbox: bool = True):
        """
        Initialise le service de paiement.

        Args:
            is_sandbox: Mode sandbox (True) ou production (False)
        """
        from django.conf import settings

        self.is_sandbox = is_sandbox
        self.payment_settings = getattr(settings, "PAYMENT_SETTINGS", {})
        self.max_retries = self.payment_settings.get("MAX_RETRIES", self.MAX_RETRIES)
        self.retry_interval = self.payment_settings.get(
            "RETRY_INTERVAL", self.RETRY_INTERVAL
        )

        logger.info(
            f"PaymentService initialized: {self.provider}, sandbox={is_sandbox}"
        )

    @abstractmethod
    def create_payment(
        self,
        amount: Decimal,
        phone: str,
        reference: str,
        user_id: int = None,
        metadata: Dict[str, Any] = None,
    ) -> PaymentResponse:
        """
        Crée une demande de paiement.

        Args:
            amount: Montant du paiement
            phone: Numéro de téléphone du client
            reference: Référence unique de la transaction
            user_id: ID de l'utilisateur (optionnel)
            metadata: Métadonnées additionnelles (optionnel)

        Returns:
            PaymentResponse: Réponse du provider
        """
        pass

    @abstractmethod
    def check_payment_status(self, transaction_id: str) -> PaymentResponse:
        """
        Vérifie le statut d'un paiement.

        Args:
            transaction_id: ID de la transaction à vérifier

        Returns:
            PaymentResponse: Réponse avec le statut actuel
        """
        pass

    @abstractmethod
    def handle_webhook(self, request_data: Dict[str, Any]) -> PaymentResponse:
        """
        Traite un webhook du provider.

        Args:
            request_data: Données du webhook

        Returns:
            PaymentResponse: Réponse du traitement
        """
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: Decimal = None) -> PaymentResponse:
        """
        Effectue un remboursement.

        Args:
            transaction_id: ID de la transaction à rembourser
            amount: Montant à rembourser (défaut: montant total)

        Returns:
            PaymentResponse: Réponse du provider
        """
        pass

    def _create_transaction_log(
        self,
        amount: Decimal,
        user,
        reference: str,
        transaction_type: str = "payment",
        **kwargs,
    ):
        """
        Crée un journal de transaction dans la base de données.

        Args:
            amount: Montant de la transaction
            user: Utilisateur effectuant le paiement
            reference: Référence unique
            transaction_type: Type de transaction
            **kwargs: Arguments additionnels

        Returns:
            TransactionLog: L'objet journal créé
        """
        from apps.payments.models import TransactionLog

        transaction = TransactionLog.objects.create(
            provider=self.provider,
            user=user,
            amount=amount,
            request_data={"reference": reference, **kwargs},
            status=TransactionLog.Status.PENDING,
        )

        logger.info(f"Transaction log created: {transaction.transaction_id}")
        return transaction

    def _schedule_retry(self, transaction_id: str, attempt_number: int):
        """
        Planifie un retry pour une transaction échouée.

        Cette méthode planifie automatiquement la relance après l'intervalle
        configuré (par défaut 1 heure).

        Args:
            transaction_id: ID de la transaction
            attempt_number: Numéro de la tentative
        """
        from apps.payments.models import TransactionLog

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)

            if attempt_number > self.max_retries:
                transaction.status = TransactionLog.Status.MAX_RETRIES_EXCEEDED
                transaction.save()
                logger.warning(f"Max retries exceeded for {transaction_id}")

                self._notify_admin_max_retries(transaction)
                return

            transaction.schedule_retry(delay_seconds=self.retry_interval)
            logger.info(
                f"Retry scheduled for {transaction_id} in {self.retry_interval}s"
            )

        except TransactionLog.DoesNotExist:
            logger.error(f"Transaction not found for retry: {transaction_id}")

    def _notify_admin_max_retries(self, transaction):
        """
        Notifie l'administrateur quand une transaction a atteint
        le nombre maximum de retries.

        Args:
            transaction: L'objet TransactionLog
        """
        from apps.notifications.models import Notification
        from apps.accounts.models import User

        admins = User.objects.filter(role="super_admin", is_active=True)

        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="Échec de paiement - Max retries",
                message=(
                    f"Le paiement {transaction.transaction_id} de "
                    f"{transaction.amount} XOF a échoué après "
                    f"{self.max_retries} tentatives. "
                    f"Utilisateur: {transaction.user.get_full_name()}"
                ),
                notification_type="error",
                priority="high",
            )


class PaymentServiceFactory:
    """
    Factory pour créer les services de paiement.

    Cette classe permet d'obtenir le bon service
    en fonction du provider demandé.

    Example:
        >>> service = PaymentServiceFactory.get_service("orange_money")
        >>> service = PaymentServiceFactory.get_service("wave")
        >>> service = PaymentServiceFactory.get_service("stripe")
    """

    _services = {
        "orange_money": None,
        "wave": None,
        "stripe": None,
    }

    @classmethod
    def get_service(cls, provider: str, is_sandbox: bool = None):
        """
        Retourne le service de paiement pour le provider demandé.

        Args:
            provider: Nom du provider (orange_money, wave, stripe)
            is_sandbox: Mode sandbox (défaut: utilise DEBUG setting)

        Returns:
            PaymentService: Le service de paiement

        Raises:
            ValueError: Si le provider n'est pas supporté
        """
        from django.conf import settings

        if is_sandbox is None:
            is_sandbox = settings.DEBUG

        if provider == "orange_money":
            if cls._services["orange_money"] is None:
                from .orange_money import OrangeMoneyService

                cls._services["orange_money"] = OrangeMoneyService(
                    is_sandbox=is_sandbox
                )
            return cls._services["orange_money"]

        elif provider == "wave":
            if cls._services["wave"] is None:
                from .wave import WaveService

                cls._services["wave"] = WaveService(is_sandbox=is_sandbox)
            return cls._services["wave"]

        elif provider == "stripe":
            if cls._services["stripe"] is None:
                from .stripe import StripePaymentService

                cls._services["stripe"] = StripePaymentService(is_sandbox=is_sandbox)
            return cls._services["stripe"]

        else:
            raise ValueError(f"Provider non supporté: {provider}")

    @classmethod
    def get_all_providers(cls):
        """
        Retourne la liste de tous les providers disponibles.

        Returns:
            list: Liste des noms de providers
        """
        return list(cls._services.keys())

    @classmethod
    def reset_services(cls):
        """
        Réinitialise tous les services (utile pour les tests).
        """
        cls._services = {
            "orange_money": None,
            "wave": None,
            "stripe": None,
        }
