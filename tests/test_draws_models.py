from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from apps.accounts.models import User
from apps.tontines.models import Tontine, Cycle
from apps.draws.models import Draw, DrawParticipant, DrawWinner, DrawHistory
from apps.contributions.models import Contribution


class DrawModelTest(TestCase):
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
        self.draw = Draw.objects.create(
            cycle=self.cycle,
            tontine=self.tontine,
            number=1,
            name="Tirage 1",
            created_by=self.user,
            total_pot=Decimal("50000.00"),
            prize_amount=Decimal("50000.00"),
        )

    def test_draw_creation(self):
        self.assertEqual(self.draw.cycle, self.cycle)
        self.assertEqual(self.draw.tontine, self.tontine)
        self.assertEqual(self.draw.status, Draw.Status.PLANIFIE)

    def test_draw_str(self):
        self.assertEqual(str(self.draw), f"{self.tontine.name} - Tirage 1")

    def test_draw_status_choices(self):
        self.assertIn(Draw.Status.PLANIFIE, Draw.Status.values)
        self.assertIn(Draw.Status.EN_COURS, Draw.Status.values)
        self.assertIn(Draw.Status.TERMINEE, Draw.Status.values)
        self.assertIn(Draw.Status.ANNULE, Draw.Status.values)

    def test_selection_method_choices(self):
        self.assertIn(Draw.SelectionMethod.ALEATOIRE, Draw.SelectionMethod.values)
        self.assertIn(Draw.SelectionMethod.ORDRE_ARRIVEE, Draw.SelectionMethod.values)
        self.assertIn(Draw.SelectionMethod.CONSENSUS, Draw.SelectionMethod.values)

    def test_get_eligible_participants(self):
        participants = self.draw.get_eligible_participants()
        self.assertEqual(len(participants), 0)

    def test_participation_count_property(self):
        self.assertEqual(self.draw.participation_count, 0)

    def test_winner_count_actual_property(self):
        self.assertEqual(self.draw.winner_count_actual, 0)

    def test_draw_unique_together(self):
        with self.assertRaises(Exception):
            Draw.objects.create(
                cycle=self.cycle,
                tontine=self.tontine,
                number=1,
                name="Duplicate Draw",
                created_by=self.user,
            )


class DrawParticipantModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="participant",
            email="participant@example.com",
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
        self.draw = Draw.objects.create(
            cycle=self.cycle,
            tontine=self.tontine,
            number=1,
            name="Tirage 1",
            created_by=self.creator,
        )
        self.participant = DrawParticipant.objects.create(
            draw=self.draw,
            user=self.user,
        )

    def test_participant_creation(self):
        self.assertEqual(self.participant.draw, self.draw)
        self.assertEqual(self.participant.user, self.user)
        self.assertTrue(self.participant.is_eligible)

    def test_participant_str(self):
        self.assertEqual(str(self.participant), f"{self.user} - {self.draw}")

    def test_participant_unique_together(self):
        with self.assertRaises(Exception):
            DrawParticipant.objects.create(
                draw=self.draw,
                user=self.user,
            )


class DrawWinnerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="winner",
            email="winner@example.com",
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
        self.draw = Draw.objects.create(
            cycle=self.cycle,
            tontine=self.tontine,
            number=1,
            name="Tirage 1",
            created_by=self.creator,
        )
        self.winner = DrawWinner.objects.create(
            draw=self.draw,
            winner=self.user,
            prize_amount=Decimal("50000.00"),
            position=1,
        )

    def test_winner_creation(self):
        self.assertEqual(self.winner.draw, self.draw)
        self.assertEqual(self.winner.winner, self.user)
        self.assertEqual(self.winner.prize_amount, Decimal("50000.00"))
        self.assertEqual(self.winner.status, DrawWinner.Status.EN_ATTENTE)

    def test_winner_str(self):
        expected = f"{self.user} - 50000.00 XAF (#1)"
        self.assertEqual(str(self.winner), expected)

    def test_winner_status_choices(self):
        self.assertIn(DrawWinner.Status.EN_ATTENTE, DrawWinner.Status.values)
        self.assertIn(DrawWinner.Status.TRANSFERT_EN_COURS, DrawWinner.Status.values)
        self.assertIn(DrawWinner.Status.TRANSFERT_REUSSI, DrawWinner.Status.values)


class DrawHistoryModelTest(TestCase):
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
        self.draw = Draw.objects.create(
            cycle=self.cycle,
            tontine=self.tontine,
            number=1,
            name="Tirage 1",
            created_by=self.user,
        )
        self.history = DrawHistory.objects.create(
            draw=self.draw,
            action="create",
            description="Tirage créé",
            performed_by=self.user,
        )

    def test_history_creation(self):
        self.assertEqual(self.history.draw, self.draw)
        self.assertEqual(self.history.action, "create")
        self.assertEqual(self.history.performed_by, self.user)

    def test_history_str(self):
        expected = f"{self.draw} - create"
        self.assertEqual(str(self.history), expected)
