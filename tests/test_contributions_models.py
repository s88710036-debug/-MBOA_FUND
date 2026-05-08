from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.accounts.models import User
from apps.tontines.models import Tontine, Cycle
from apps.contributions.models import (
    Contribution,
    MobileMoneyTransaction,
    PaymentRequest,
    Payout,
)


class ContributionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="contributor",
            email="contributor@example.com",
            password="testpass123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            creator=self.creator,
            amount_per_member=10000,
        )
        self.cycle = Cycle.objects.create(
            tontine=self.tontine,
            number=1,
            name="Cycle 1",
            start_date=timezone.now().date(),
            amount_per_member=10000,
            total_expected=50000,
        )

    def test_contribution_creation(self):
        contribution = Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.ORANGE_MONEY,
        )
        self.assertEqual(contribution.user, self.user)
        self.assertEqual(contribution.amount, Decimal("10000.00"))
        self.assertEqual(contribution.status, Contribution.Status.EN_ATTENTE)

    def test_contribution_str(self):
        contribution = Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.WAVE,
        )
        self.assertIn("10000", str(contribution))

    def test_contribution_is_paid_property(self):
        contribution = Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.ORANGE_MONEY,
        )
        self.assertFalse(contribution.is_paid)
        contribution.status = Contribution.Status.VALIDE
        contribution.save()
        self.assertTrue(contribution.is_paid)

    def test_contribution_is_pending_property(self):
        contribution = Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.ORANGE_MONEY,
        )
        self.assertTrue(contribution.is_pending)
        contribution.status = Contribution.Status.VALIDE
        contribution.save()
        self.assertFalse(contribution.is_pending)

    def test_contribution_unique_together(self):
        Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.ORANGE_MONEY,
        )
        with self.assertRaises(Exception):
            Contribution.objects.create(
                user=self.user,
                cycle=self.cycle,
                tontine=self.tontine,
                amount=Decimal("5000.00"),
                payment_method=Contribution.PaymentMethod.WAVE,
            )

    def test_payment_method_choices(self):
        self.assertIn(
            Contribution.PaymentMethod.ORANGE_MONEY, Contribution.PaymentMethod.values
        )
        self.assertIn(
            Contribution.PaymentMethod.WAVE, Contribution.PaymentMethod.values
        )
        self.assertIn(
            Contribution.PaymentMethod.CASH, Contribution.PaymentMethod.values
        )

    def test_status_choices(self):
        self.assertIn(Contribution.Status.EN_ATTENTE, Contribution.Status.values)
        self.assertIn(Contribution.Status.VALIDE, Contribution.Status.values)
        self.assertIn(Contribution.Status.REJETE, Contribution.Status.values)


class MobileMoneyTransactionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            creator=self.creator,
            amount_per_member=10000,
        )
        self.cycle = Cycle.objects.create(
            tontine=self.tontine,
            number=1,
            name="Cycle 1",
            start_date=timezone.now().date(),
            amount_per_member=10000,
            total_expected=50000,
        )
        self.contribution = Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.ORANGE_MONEY,
        )

    def test_transaction_creation(self):
        transaction = MobileMoneyTransaction.objects.create(
            contribution=self.contribution,
            provider=MobileMoneyTransaction.Provider.ORANGE,
            amount=Decimal("10000.00"),
            sender_phone="+221771234567",
            receiver_phone="+221773456789",
        )
        self.assertEqual(transaction.provider, MobileMoneyTransaction.Provider.ORANGE)
        self.assertEqual(
            transaction.status, MobileMoneyTransaction.TransactionStatus.PENDING
        )

    def test_transaction_str(self):
        transaction = MobileMoneyTransaction.objects.create(
            contribution=self.contribution,
            provider=MobileMoneyTransaction.Provider.WAVE,
            amount=Decimal("10000.00"),
            sender_phone="+221771234567",
            receiver_phone="+221773456789",
        )
        self.assertIn("wave", str(transaction))
        self.assertIn("10000", str(transaction))


class PaymentRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            creator=self.creator,
            amount_per_member=10000,
        )
        self.cycle = Cycle.objects.create(
            tontine=self.tontine,
            number=1,
            name="Cycle 1",
            start_date=timezone.now().date(),
            amount_per_member=10000,
            total_expected=50000,
        )
        self.contribution = Contribution.objects.create(
            user=self.user,
            cycle=self.cycle,
            tontine=self.tontine,
            amount=Decimal("10000.00"),
            payment_method=Contribution.PaymentMethod.ORANGE_MONEY,
        )

    def test_payment_request_creation(self):
        payment_request = PaymentRequest.objects.create(
            contribution=self.contribution,
            amount=Decimal("10000.00"),
            payment_method=PaymentRequest.PaymentMethod.ORANGE_MONEY,
            payment_token="test_token_12345",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.assertEqual(payment_request.status, PaymentRequest.Status.PENDING)
        self.assertIsNotNone(payment_request.payment_token)

    def test_payment_request_str(self):
        payment_request = PaymentRequest.objects.create(
            contribution=self.contribution,
            amount=Decimal("10000.00"),
            payment_method=PaymentRequest.PaymentMethod.WAVE,
            payment_token="test_token_67890",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.assertIn("test_tok", str(payment_request))


class PayoutModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recipient",
            email="recipient@example.com",
            password="testpass123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            creator=self.creator,
            amount_per_member=10000,
        )

    def test_payout_creation(self):
        payout = Payout.objects.create(
            tontine=self.tontine,
            recipient=self.user,
            amount=Decimal("50000.00"),
            payment_method=Payout.PaymentMethod.ORANGE_MONEY,
            recipient_phone="+221771234567",
        )
        self.assertEqual(payout.status, Payout.Status.PENDING)
        self.assertEqual(payout.amount, Decimal("50000.00"))

    def test_payout_str(self):
        payout = Payout.objects.create(
            tontine=self.tontine,
            recipient=self.user,
            amount=Decimal("50000.00"),
            payment_method=Payout.PaymentMethod.WAVE,
            recipient_phone="+221771234567",
        )
        self.assertIn("50000", str(payout))

    def test_payout_status_choices(self):
        self.assertIn(Payout.Status.PENDING, Payout.Status.values)
        self.assertIn(Payout.Status.PROCESSING, Payout.Status.values)
        self.assertIn(Payout.Status.COMPLETED, Payout.Status.values)
        self.assertIn(Payout.Status.FAILED, Payout.Status.values)
