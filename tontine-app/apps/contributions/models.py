import uuid
from django.db import models
from django.conf import settings
from apps.tontines.models import Tontine, Cycle


class Contribution(models.Model):
    class Status(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        EN_COURS = "en_cours", "En cours de vérification"
        VALIDE = "valide", "Validée"
        REJETE = "rejete", "Rejetée"
        REMBOURSE = "rembourse", "Remboursée"

    class PaymentMethod(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        WAVE = "wave", "Wave"
        WESTERN_UNION = "western_union", "Western Union"
        BANK_TRANSFER = "bank_transfer", "Virement bancaire"
        CASH = "cash", "Espèces"
        OTHER = "other", "Autre"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contributions"
    )
    cycle = models.ForeignKey(
        Cycle, on_delete=models.CASCADE, related_name="contributions"
    )
    tontine = models.ForeignKey(
        Tontine, on_delete=models.CASCADE, related_name="contributions"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.EN_ATTENTE
    )

    reference_number = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    sender_name = models.CharField(max_length=200, blank=True)
    sender_phone = models.CharField(max_length=20, blank=True)
    receiver_phone = models.CharField(max_length=20, blank=True)

    proof_document = models.FileField(
        upload_to="contributions/proofs/", blank=True, null=True
    )
    notes = models.TextField(blank=True)

    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validated_contributions",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cotisation"
        verbose_name_plural = "Cotisations"
        ordering = ["-created_at"]
        unique_together = ("user", "cycle")

    def __str__(self):
        return f"{self.user} - {self.cycle} - {self.amount} XAF"

    @property
    def is_paid(self):
        return self.status == self.Status.VALIDE

    @property
    def is_pending(self):
        return self.status in [self.Status.EN_ATTENTE, self.Status.EN_COURS]


class MobileMoneyTransaction(models.Model):
    class Provider(models.TextChoices):
        ORANGE = "orange", "Orange Money"
        WAVE = "wave", "Wave"

    class TransactionStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        SUCCESS = "success", "Succès"
        FAILED = "failed", "Échoué"
        CANCELLED = "cancelled", "Annulé"
        REFUNDED = "refunded", "Remboursé"

    contribution = models.ForeignKey(
        Contribution, on_delete=models.CASCADE, related_name="transactions"
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")

    sender_phone = models.CharField(max_length=20)
    receiver_phone = models.CharField(max_length=20)

    external_transaction_id = models.CharField(max_length=100, blank=True)
    merchant_transaction_id = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )

    callback_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Transaction Mobile Money"
        verbose_name_plural = "Transactions Mobile Money"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} - {self.amount} - {self.status}"


class PaymentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PAID = "paid", "Payé"
        EXPIRED = "expired", "Expiré"
        CANCELLED = "cancelled", "Annulé"

    class PaymentMethod(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        WAVE = "wave", "Wave"

    contribution = models.ForeignKey(
        Contribution, on_delete=models.CASCADE, related_name="payment_requests"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    merchant_id = models.CharField(max_length=100, blank=True)

    payment_token = models.CharField(max_length=200, unique=True)
    payment_url = models.URLField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    expires_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Demande de paiement"
        verbose_name_plural = "Demandes de paiement"

    def __str__(self):
        return f"Payment {self.payment_token[:8]} - {self.amount} XOF"


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        PROCESSING = "processing", "En cours"
        COMPLETED = "completed", "Complété"
        FAILED = "failed", "Échoué"

    class PaymentMethod(models.TextChoices):
        ORANGE_MONEY = "orange_money", "Orange Money"
        WAVE = "wave", "Wave"
        BANK_TRANSFER = "bank_transfer", "Virement bancaire"

    tontine = models.ForeignKey(
        Tontine, on_delete=models.CASCADE, related_name="payouts"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payouts"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    recipient_phone = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    transaction_id = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="processed_payouts",
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payout {self.recipient} - {self.amount} XAF"
