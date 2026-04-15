from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from apps.accounts.models import User
from apps.payments.models import (
    TransactionLog,
    SMSNotificationLog,
    PaymentDashboardCache,
)


class TransactionLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )

    def test_transaction_log_creation(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.ORANGE_MONEY,
            user=self.user,
            amount=Decimal("10000.00"),
            status=TransactionLog.Status.PENDING,
        )
        self.assertIsNotNone(transaction.transaction_id)
        self.assertTrue(transaction.transaction_id.startswith("TXN_"))

    def test_transaction_log_str(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.WAVE,
            user=self.user,
            amount=Decimal("10000.00"),
        )
        self.assertIn("wave", str(transaction).lower())

    def test_mark_success(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.ORANGE_MONEY,
            user=self.user,
            amount=Decimal("10000.00"),
        )
        transaction.mark_success({"status": "success"})
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, TransactionLog.Status.SUCCESS)
        self.assertIsNotNone(transaction.completed_at)

    def test_mark_failed(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.ORANGE_MONEY,
            user=self.user,
            amount=Decimal("10000.00"),
        )
        transaction.mark_failed("Payment failed", {"error": "insufficient_funds"})
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, TransactionLog.Status.FAILED)
        self.assertEqual(transaction.error_message, "Payment failed")

    def test_schedule_retry(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.ORANGE_MONEY,
            user=self.user,
            amount=Decimal("10000.00"),
        )
        transaction.schedule_retry(delay_seconds=1800)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, TransactionLog.Status.RETRY_SCHEDULED)
        self.assertEqual(transaction.retry_count, 1)
        self.assertIsNotNone(transaction.next_retry_at)

    def test_is_completed_property(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.ORANGE_MONEY,
            user=self.user,
            amount=Decimal("10000.00"),
        )
        self.assertFalse(transaction.is_completed)
        transaction.status = TransactionLog.Status.SUCCESS
        transaction.save()
        self.assertTrue(transaction.is_completed)

    def test_can_retry_property(self):
        transaction = TransactionLog.objects.create(
            provider=TransactionLog.Provider.ORANGE_MONEY,
            user=self.user,
            amount=Decimal("10000.00"),
        )
        self.assertFalse(transaction.can_retry)
        transaction.status = TransactionLog.Status.FAILED
        transaction.save()
        self.assertTrue(transaction.can_retry)

    def test_provider_choices(self):
        self.assertIn(
            TransactionLog.Provider.ORANGE_MONEY, TransactionLog.Provider.values
        )
        self.assertIn(TransactionLog.Provider.WAVE, TransactionLog.Provider.values)
        self.assertIn(TransactionLog.Provider.STRIPE, TransactionLog.Provider.values)


class SMSNotificationLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )

    def test_sms_notification_creation(self):
        sms = SMSNotificationLog.objects.create(
            phone_number="+221771234567",
            message="Test message",
            provider=SMSNotificationLog.Provider.AFRICAS_TALKING,
            user=self.user,
        )
        self.assertEqual(sms.status, SMSNotificationLog.Status.PENDING)

    def test_sms_notification_str(self):
        sms = SMSNotificationLog.objects.create(
            phone_number="+221771234567",
            message="Test message",
            provider=SMSNotificationLog.Provider.AFRICAS_TALKING,
        )
        self.assertIn("+221771234567", str(sms))

    def test_sms_provider_choices(self):
        self.assertIn(
            SMSNotificationLog.Provider.AFRICAS_TALKING,
            SMSNotificationLog.Provider.values,
        )
        self.assertIn(
            SMSNotificationLog.Provider.ORANGE, SMSNotificationLog.Provider.values
        )

    def test_sms_status_choices(self):
        self.assertIn(
            SMSNotificationLog.Status.PENDING, SMSNotificationLog.Status.values
        )
        self.assertIn(SMSNotificationLog.Status.SENT, SMSNotificationLog.Status.values)
        self.assertIn(
            SMSNotificationLog.Status.FAILED, SMSNotificationLog.Status.values
        )


class PaymentDashboardCacheModelTest(TestCase):
    def test_dashboard_cache_creation(self):
        from datetime import date

        cache = PaymentDashboardCache.objects.create(
            date=date.today(),
            total_transactions=10,
            total_amount=Decimal("100000.00"),
            successful_amount=Decimal("90000.00"),
            failed_amount=Decimal("10000.00"),
        )
        self.assertEqual(cache.total_transactions, 10)

    def test_dashboard_cache_str(self):
        from datetime import date

        cache = PaymentDashboardCache.objects.create(date=date.today())
        today = date.today()
        self.assertEqual(str(cache), f"Dashboard {today}")

    def test_dashboard_cache_unique_date(self):
        from datetime import date

        PaymentDashboardCache.objects.create(date=date.today())
        with self.assertRaises(Exception):
            PaymentDashboardCache.objects.create(date=date.today())
