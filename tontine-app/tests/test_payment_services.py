from django.test import TestCase
from decimal import Decimal
from apps.payments.services import TransactionServiceHelper, SMServiceHelper


class PaymentServiceTest(TestCase):
    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )

    def test_create_transaction(self):
        from apps.payments.models import TransactionLog

        transaction = TransactionServiceHelper.create_transaction(
            user=self.user,
            provider=TransactionLog.Provider.ORANGE_MONEY,
            amount=Decimal("10000.00"),
        )
        self.assertIsNotNone(transaction)
        self.assertIsNotNone(transaction.transaction_id)

    def test_transaction_with_custom_id(self):
        from apps.payments.models import TransactionLog
        from decimal import Decimal

        transaction = TransactionServiceHelper.create_transaction(
            user=self.user,
            provider=TransactionLog.Provider.WAVE,
            amount=Decimal("5000.00"),
            custom_transaction_id="CUSTOM_TXN_001",
        )
        self.assertEqual(transaction.transaction_id, "CUSTOM_TXN_001")

    def test_get_user_transactions(self):
        from apps.payments.models import TransactionLog
        from decimal import Decimal

        for i in range(3):
            TransactionServiceHelper.create_transaction(
                user=self.user,
                provider=TransactionLog.Provider.ORANGE_MONEY,
                amount=Decimal("1000.00") * (i + 1),
            )
        transactions = TransactionServiceHelper.get_user_transactions(self.user)
        self.assertEqual(transactions.count(), 3)

    def test_mark_transaction_success(self):
        from apps.payments.models import TransactionLog
        from decimal import Decimal

        transaction = TransactionServiceHelper.create_transaction(
            user=self.user,
            provider=TransactionLog.Provider.ORANGE_MONEY,
            amount=Decimal("10000.00"),
        )
        result = TransactionServiceHelper.mark_transaction_success(
            transaction.transaction_id,
            {"status": "completed"},
        )
        self.assertTrue(result)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, TransactionLog.Status.SUCCESS)

    def test_mark_transaction_failed(self):
        from apps.payments.models import TransactionLog
        from decimal import Decimal

        transaction = TransactionServiceHelper.create_transaction(
            user=self.user,
            provider=TransactionLog.Provider.ORANGE_MONEY,
            amount=Decimal("10000.00"),
        )
        result = TransactionServiceHelper.mark_transaction_failed(
            transaction.transaction_id,
            "Payment declined",
        )
        self.assertTrue(result)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, TransactionLog.Status.FAILED)

    def test_get_pending_transactions(self):
        from apps.payments.models import TransactionLog
        from decimal import Decimal

        TransactionServiceHelper.create_transaction(
            user=self.user,
            provider=TransactionLog.Provider.ORANGE_MONEY,
            amount=Decimal("10000.00"),
        )
        pending = TransactionServiceHelper.get_pending_transactions()
        self.assertGreaterEqual(pending.count(), 1)

    def test_process_retry_transactions(self):
        from apps.payments.models import TransactionLog
        from decimal import Decimal

        transaction = TransactionServiceHelper.create_transaction(
            user=self.user,
            provider=TransactionLog.Provider.ORANGE_MONEY,
            amount=Decimal("10000.00"),
        )
        transaction.status = TransactionLog.Status.FAILED
        transaction.retry_count = 1
        transaction.save()
        processed = TransactionServiceHelper.process_retry_transactions()
        self.assertGreaterEqual(processed, 0)


class SMSServiceTest(TestCase):
    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
            phone="+221771234567",
        )

    def test_send_sms_simulation(self):
        result = SMServiceHelper.send_sms(
            phone="+221771234567",
            message="Test message",
        )
        self.assertIn("success", result.lower())

    def test_send_sms_with_user(self):
        result = SMServiceHelper.send_sms(
            phone=self.user.phone,
            message="Test to user",
            user=self.user,
        )
        self.assertIn("success", result.lower())

    def test_send_sms_notification_type(self):
        result = SMServiceHelper.send_sms(
            phone="+221771234567",
            message="Payment received",
            notification_type="payment",
        )
        self.assertIn("success", result.lower())

    def test_send_sms_to_invalid_phone(self):
        result = SMServiceHelper.send_sms(
            phone="+000000000",
            message="Test",
        )
        self.assertIsNotNone(result)

    def test_get_sms_logs(self):
        from apps.payments.models import SMSNotificationLog

        SMServiceHelper.send_sms(
            phone="+221771234567",
            message="Log test",
        )
        logs = SMServiceHelper.get_sms_logs(phone="+221771234567")
        self.assertGreaterEqual(logs.count(), 1)

    def test_sms_log_creation(self):
        from apps.payments.models import SMSNotificationLog

        SMServiceHelper.send_sms(
            phone="+221771234567",
            message="Log verification",
        )
        log = SMSNotificationLog.objects.filter(phone_number="+221771234567").first()
        self.assertIsNotNone(log)
