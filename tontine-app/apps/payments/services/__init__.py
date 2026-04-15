"""
Services de paiement pour Tontine-App.

Ce module contient les services pour:
- Orange Money
- Wave
- Stripe
"""

from .base import PaymentService, PaymentServiceFactory, PaymentResponse
from .orange_money import OrangeMoneyService
from .wave import WaveService
from .stripe import StripePaymentService
from .notification import SMSNotificationService

from apps.payments.models import TransactionLog, SMSNotificationLog


class TransactionServiceHelper:
    @staticmethod
    def create_transaction(
        user,
        provider,
        amount,
        tontine=None,
        contribution=None,
        custom_transaction_id=None,
        request_data=None,
    ):
        transaction = TransactionLog.objects.create(
            provider=provider,
            user=user,
            tontine=tontine,
            contribution=contribution,
            amount=amount,
            request_data=request_data or {},
        )
        if custom_transaction_id:
            transaction.transaction_id = custom_transaction_id
            transaction.save()
        return transaction

    @staticmethod
    def get_user_transactions(user, status=None):
        qs = TransactionLog.objects.filter(user=user)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def mark_transaction_success(transaction_id, response_data=None):
        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
            transaction.mark_success(response_data=response_data)
            return True
        except TransactionLog.DoesNotExist:
            return False

    @staticmethod
    def mark_transaction_failed(transaction_id, error_message, response_data=None):
        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
            transaction.mark_failed(error_message, response_data=response_data)
            return True
        except TransactionLog.DoesNotExist:
            return False

    @staticmethod
    def get_pending_transactions():
        return TransactionLog.objects.filter(status=TransactionLog.Status.PENDING)

    @staticmethod
    def process_retry_transactions():
        retry_transactions = TransactionLog.objects.filter(
            status__in=[
                TransactionLog.Status.FAILED,
                TransactionLog.Status.RETRY_SCHEDULED,
            ],
            next_retry_at__lte=timezone.now(),
        )
        count = 0
        for transaction in retry_transactions:
            if transaction.can_retry:
                transaction.schedule_retry()
                count += 1
        return count


class SMServiceHelper:
    @staticmethod
    def send_sms(phone, message, user=None, notification_type="general"):
        try:
            log = SMSNotificationLog.objects.create(
                phone_number=phone,
                message=message,
                provider=SMSNotificationLog.Provider.AFRICAS_TALKING,
                user=user,
                notification_type=notification_type,
                status=SMSNotificationLog.Status.SENT,
                sent_at=timezone.now(),
            )
            return "success"
        except Exception as e:
            log = SMSNotificationLog.objects.create(
                phone_number=phone,
                message=message,
                provider=SMSNotificationLog.Provider.AFRICAS_TALKING,
                user=user,
                notification_type=notification_type,
                status=SMSNotificationLog.Status.FAILED,
                error_message=str(e),
            )
            return "error"

    @staticmethod
    def get_sms_logs(phone=None, status=None, limit=None):
        qs = SMSNotificationLog.objects.all()
        if phone:
            qs = qs.filter(phone_number=phone)
        if status:
            qs = qs.filter(status=status)
        if limit:
            qs = qs[:limit]
        return qs


from django.utils import timezone


__all__ = [
    "PaymentService",
    "PaymentServiceFactory",
    "PaymentResponse",
    "OrangeMoneyService",
    "WaveService",
    "StripePaymentService",
    "SMSNotificationService",
    "TransactionServiceHelper",
    "SMServiceHelper",
]
