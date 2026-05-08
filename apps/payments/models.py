"""
Modèles pour la gestion des paiements.
Inclut le journal des transactions, les logs SMS et le cache du dashboard.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class TransactionLog(models.Model):
    """
    Journal de toutes les transactions de paiement.

    Ce modèle enregistre chaque tentative de paiement,
    permettant un suivi complet et un debugging facile.
    """

    class Provider(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        WAVE = "wave", "Wave"
        STRIPE = "stripe", "Stripe (Cartes)"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PROCESSING = "processing", "En cours"
        SUCCESS = "success", "Succès"
        FAILED = "failed", "Échoué"
        CANCELLED = "cancelled", "Annulé"
        REFUNDED = "refunded", "Remboursé"
        RETRY_SCHEDULED = "retry_scheduled", "Retry planifié"
        MAX_RETRIES_EXCEEDED = "max_retries_exceeded", "Max retries dépassé"

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        help_text="Identifiant unique de la transaction",
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        help_text="Provider de paiement utilisé",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )
    tontine = models.ForeignKey(
        "tontines.Tontine",
        on_delete=models.CASCADE,
        related_name="payment_transactions",
        null=True,
        blank=True,
    )
    contribution = models.ForeignKey(
        "contributions.Contribution",
        on_delete=models.CASCADE,
        related_name="payment_transactions",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Montant en XOF"
    )
    currency = models.CharField(max_length=3, default="XOF")
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING
    )
    retry_count = models.IntegerField(
        default=0, help_text="Nombre de tentatives de retry"
    )
    next_retry_at = models.DateTimeField(
        null=True, blank=True, help_text="Date du prochain retry"
    )
    request_data = models.JSONField(
        default=dict, blank=True, help_text="Données de la requête API"
    )
    response_data = models.JSONField(
        default=dict, blank=True, help_text="Données de la réponse API"
    )
    error_message = models.TextField(blank=True, help_text="Message d'erreur si échec")
    callback_data = models.JSONField(
        default=dict, blank=True, help_text="Données reçues par webhook"
    )
    payment_url = models.URLField(
        blank=True, help_text="URL de redirection vers le provider"
    )
    external_transaction_id = models.CharField(
        max_length=200, blank=True, help_text="ID de transaction chez le provider"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Journal de Transaction"
        verbose_name_plural = "Journaux de Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.provider} - {self.transaction_id} - {self.amount} XOF"

    def save(self, *args, **kwargs):
        """Génère un transaction_id unique si non défini."""
        if not self.transaction_id:
            self.transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def mark_success(self, response_data=None):
        """Marque la transaction comme réussie."""
        self.status = self.Status.SUCCESS
        self.completed_at = timezone.now()
        if response_data:
            self.response_data = response_data
        self.save()

    def mark_failed(self, error_message, response_data=None):
        """Marque la transaction comme échouée."""
        self.status = self.Status.FAILED
        self.error_message = error_message
        if response_data:
            self.response_data = response_data
        self.save()

    def schedule_retry(self, delay_seconds=3600):
        """Planifie un retry pour cette transaction."""
        from datetime import timedelta

        self.retry_count += 1
        self.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.status = self.Status.RETRY_SCHEDULED
        self.save()

    @property
    def is_completed(self):
        """Vérifie si la transaction est terminée (succès ou échec permanent)."""
        return self.status in [
            self.Status.SUCCESS,
            self.Status.CANCELLED,
            self.Status.REFUNDED,
            self.Status.MAX_RETRIES_EXCEEDED,
        ]

    @property
    def can_retry(self):
        """Vérifie si la transaction peut être relancée."""
        from django.conf import settings

        max_retries = settings.PAYMENT_SETTINGS.get("MAX_RETRIES", 3)
        return (
            self.status in [self.Status.FAILED, self.Status.RETRY_SCHEDULED]
            and self.retry_count < max_retries
        )


class SMSNotificationLog(models.Model):
    """
    Journal des notifications SMS envoyées.

    Permet de suivre l'historique des SMS
    et de gérer les retries en cas d'échec.
    """

    class Provider(models.TextChoices):
        AFRICAS_TALKING = "africas_talking", "Africa's Talking"
        ORANGE = "orange", "Orange SMS"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        SENT = "sent", "Envoyé"
        DELIVERED = "delivered", "Livré"
        FAILED = "failed", "Échoué"
        RETRY = "retry", "En retry"

    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    provider = models.CharField(max_length=30, choices=Provider.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_notifications",
        null=True,
        blank=True,
    )
    transaction = models.ForeignKey(
        TransactionLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_notifications",
    )
    notification_type = models.CharField(max_length=50, blank=True, default="general")
    external_id = models.CharField(max_length=100, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Log Notification SMS"
        verbose_name_plural = "Logs Notifications SMS"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SMS à {self.phone_number} - {self.status}"


class PaymentDashboardCache(models.Model):
    """
    Cache des métriques du dashboard financier.

    Ce modèle stocke les agrégations des transactions
    pour un accès rapide aux statistiques.
    """

    date = models.DateField(unique=True)

    total_transactions = models.IntegerField(default=0)
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    successful_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    failed_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    orange_transactions = models.IntegerField(default=0)
    orange_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    wave_transactions = models.IntegerField(default=0)
    wave_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    stripe_transactions = models.IntegerField(default=0)
    stripe_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cache Dashboard"
        verbose_name_plural = "Caches Dashboard"
        ordering = ["-date"]

    def __str__(self):
        return f"Dashboard {self.date}"
