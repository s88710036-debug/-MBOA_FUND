from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.tontines.models import Tontine, TontineMembership, Cycle


class TontineModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            description="Description test",
            creator=self.user,
            amount_per_member=10000,
            min_members=3,
            max_members=10,
        )

    def test_tontine_creation(self):
        self.assertEqual(self.tontine.name, "Tontine Test")
        self.assertEqual(self.tontine.status, Tontine.Status.EN_CREATION)
        self.assertEqual(self.tontine.creator, self.user)
        self.assertIsNotNone(self.tontine.invite_code)
        self.assertEqual(len(self.tontine.invite_code), 8)

    def test_tontine_str(self):
        self.assertEqual(str(self.tontine), "Tontine Test")

    def test_tontine_uuid_unique(self):
        self.assertIsNotNone(self.tontine.uuid)

    def test_tontine_status_choices(self):
        self.assertIn(Tontine.Status.EN_CREATION, Tontine.Status.values)
        self.assertIn(Tontine.Status.ACTIVE, Tontine.Status.values)
        self.assertIn(Tontine.Status.TERMINEE, Tontine.Status.values)
        self.assertIn(Tontine.Status.ANNULEE, Tontine.Status.values)

    def test_tontine_frequency_choices(self):
        self.assertIn(Tontine.Frequency.HEBDOMADAIRE, Tontine.Frequency.values)
        self.assertIn(Tontine.Frequency.BI_WEEKLY, Tontine.Frequency.values)
        self.assertIn(Tontine.Frequency.MENSUEL, Tontine.Frequency.values)

    def test_member_count_property(self):
        self.assertEqual(self.tontine.member_count, 0)

    def test_is_full_property(self):
        self.assertFalse(self.tontine.is_full)

    def test_can_start_property(self):
        self.assertFalse(self.tontine.can_start)


class TontineMembershipModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="testpass123",
        )
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            creator=self.creator,
            amount_per_member=10000,
        )
        self.membership = TontineMembership.objects.create(
            tontine=self.tontine,
            user=self.user,
            role=TontineMembership.Role.MEMBRE,
            status=TontineMembership.Status.ACTIF,
        )

    def test_membership_creation(self):
        self.assertEqual(self.membership.tontine, self.tontine)
        self.assertEqual(self.membership.user, self.user)
        self.assertEqual(self.membership.role, TontineMembership.Role.MEMBRE)

    def test_membership_str(self):
        expected = f"{self.user} - {self.tontine} (Membre)"
        self.assertEqual(str(self.membership), expected)

    def test_is_tresorier_property(self):
        self.assertFalse(self.membership.is_tresorier)
        self.membership.role = TontineMembership.Role.TRESORIER
        self.membership.save()
        self.assertTrue(self.membership.is_tresorier)

    def test_can_contribute_property(self):
        self.assertFalse(self.membership.can_contribute)
        self.tontine.status = Tontine.Status.ACTIVE
        self.tontine.save()
        self.assertTrue(self.membership.can_contribute)

    def test_membership_unique_together(self):
        with self.assertRaises(Exception):
            TontineMembership.objects.create(
                tontine=self.tontine,
                user=self.user,
            )

    def test_tresorier_membership(self):
        tresorier = User.objects.create_user(
            username="tresorier",
            email="tresorier@example.com",
            password="testpass123",
        )
        membership = TontineMembership.objects.create(
            tontine=self.tontine,
            user=tresorier,
            role=TontineMembership.Role.TRESORIER,
        )
        self.assertTrue(membership.is_tresorier)


class CycleModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="testpass123",
        )
        self.tontine = Tontine.objects.create(
            name="Tontine Test",
            creator=self.user,
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

    def test_cycle_creation(self):
        self.assertEqual(self.cycle.tontine, self.tontine)
        self.assertEqual(self.cycle.number, 1)
        self.assertEqual(self.cycle.status, Cycle.Status.EN_COURS)

    def test_cycle_str(self):
        expected = f"{self.tontine.name} - Cycle 1"
        self.assertEqual(str(self.cycle), expected)

    def test_cycle_unique_together(self):
        with self.assertRaises(Exception):
            Cycle.objects.create(
                tontine=self.tontine,
                number=1,
                name="Duplicate Cycle",
                start_date=timezone.now().date(),
                amount_per_member=10000,
                total_expected=50000,
            )

    def test_total_amount_property(self):
        self.assertEqual(self.cycle.total_amount, 0)

    def test_contribution_count_property(self):
        self.assertEqual(self.cycle.contribution_count, 0)

    def test_remaining_amount_property(self):
        self.assertEqual(self.cycle.remaining_amount, 50000)

    def test_participation_rate_property(self):
        self.assertEqual(self.cycle.participation_rate, 0)

    def test_cycle_is_active(self):
        self.assertTrue(self.cycle.is_active is False)
        self.cycle.is_active = True
        self.cycle.save()
        self.cycle.refresh_from_db()
        self.assertTrue(self.cycle.is_active)

    def test_get_current_cycle(self):
        self.assertEqual(self.tontine.get_current_cycle(), None)
        self.cycle.is_active = True
        self.cycle.save()
        self.assertEqual(self.tontine.get_current_cycle(), self.cycle)
