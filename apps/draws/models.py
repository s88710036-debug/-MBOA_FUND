import random
import uuid
from django.db import models
from django.conf import settings
from apps.tontines.models import Tontine, Cycle


class Draw(models.Model):
    class Status(models.TextChoices):
        PLANIFIE = "planifie", "Planifié"
        EN_COURS = "en_cours", "En cours"
        TERMINEE = "terminee", "Terminée"
        ANNULE = "annule", "Annulée"

    class SelectionMethod(models.TextChoices):
        ALEATOIRE = "aleatoire", "Aléatoire"
        ORDRE_ARRIVEE = "ordre_arrivee", "Ordre d'arrivée"
        CYCLE = "cycle", "Par cycle"
        CONSENSUS = "consensus", "Consensus des membres"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name="draws")
    tontine = models.ForeignKey(Tontine, on_delete=models.CASCADE, related_name="draws")

    number = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANIFIE
    )
    selection_method = models.CharField(
        max_length=30,
        choices=SelectionMethod.choices,
        default=SelectionMethod.ALEATOIRE,
    )

    scheduled_date = models.DateTimeField(null=True, blank=True)
    draw_date = models.DateTimeField(null=True, blank=True)

    total_pot = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    prize_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    winner_count = models.PositiveIntegerField(default=1)
    eligible_participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="DrawParticipant",
        related_name="eligible_draws",
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_draws",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tirage"
        verbose_name_plural = "Tirages"
        ordering = ["-draw_date"]
        unique_together = ("cycle", "number")

    def __str__(self):
        return f"{self.tontine.name} - {self.name}"

    def get_eligible_participants(self):
        from apps.contributions.models import Contribution

        valid_contributors = Contribution.objects.filter(
            cycle=self.cycle, status="valide"
        ).values_list("user_id", flat=True)

        active_members = self.tontine.memberships.filter(status="actif").values_list(
            "user_id", flat=True
        )

        return list(set(valid_contributors) & set(active_members))

    def perform_draw(self):
        if self.status != self.Status.PLANIFIE:
            return None

        eligible = self.get_eligible_participants()

        previous_winners = DrawWinner.objects.filter(
            draw__cycle=self.cycle
        ).values_list("winner_id", flat=True)
        still_eligible = [u for u in eligible if u not in previous_winners]

        if len(still_eligible) < self.winner_count:
            still_eligible = (
                eligible[: self.winner_count]
                if len(eligible) >= self.winner_count
                else eligible
            )

        selected = random.sample(
            still_eligible, min(self.winner_count, len(still_eligible))
        )

        self.status = self.Status.EN_COURS
        self.draw_date = timezone.now()
        self.save()

        winners = []
        for user_id in selected:
            winner = DrawWinner.objects.create(
                draw=self,
                winner_id=user_id,
                prize_amount=self.prize_amount / len(selected),
                position=selected.index(user_id) + 1,
            )
            winners.append(winner)

        self.status = self.Status.TERMINEE
        self.save()

        return winners

    @property
    def participation_count(self):
        return self.eligible_participants.count()

    @property
    def winner_count_actual(self):
        return self.winners.count()


class DrawParticipant(models.Model):
    draw = models.ForeignKey(
        Draw, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="draw_participations",
    )
    is_eligible = models.BooleanField(default=True)
    exclusion_reason = models.CharField(max_length=200, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Participant au tirage"
        verbose_name_plural = "Participants aux tirages"
        unique_together = ("draw", "user")

    def __str__(self):
        return f"{self.user} - {self.draw}"


class DrawWinner(models.Model):
    class Status(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        TRANSFERT_EN_COURS = "transfert_en_cours", "Transfert en cours"
        TRANSFERT_REUSSI = "transfert_reussi", "Transfert réussi"
        TRANSFERT_ECHEC = "transfert_echec", "Échec du transfert"
        RECU = "recu", "Reçu par le gagnant"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name="winners")
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="winnings"
    )

    prize_amount = models.DecimalField(max_digits=15, decimal_places=2)
    position = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.EN_ATTENTE
    )
    payout_reference = models.CharField(max_length=100, blank=True)

    notification_sent = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gagnant"
        verbose_name_plural = "Gagnants"
        ordering = ["position"]

    def __str__(self):
        return f"{self.winner} - {self.prize_amount} XAF (#{self.position})"


class DrawHistory(models.Model):
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=100)
    description = models.TextField()
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique de tirage"
        verbose_name_plural = "Historiques de tirages"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.draw} - {self.action}"
