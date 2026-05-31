import uuid
from django.db import models
from django.conf import settings


class Tontine(models.Model):
    class Status(models.TextChoices):
        EN_CREATION = "en_creation", "En création"
        ACTIVE = "active", "Active"
        TERMINEE = "terminee", "Terminée"
        ANNULEE = "annulee", "Annulée"

    class Frequency(models.TextChoices):
        HEBDOMADAIRE = "weekly", "Hebdomadaire"
        BI_WEEKLY = "bi_weekly", "Bi-hebdomadaire"
        MENSUEL = "monthly", "Mensuel"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tontines",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.EN_CREATION
    )
    frequency = models.CharField(
        max_length=20, choices=Frequency.choices, default=Frequency.MENSUEL
    )
    amount_per_member = models.DecimalField(max_digits=12, decimal_places=2)
    max_members = models.PositiveIntegerField(default=20)
    min_members = models.PositiveIntegerField(default=3)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    invite_code = models.CharField(max_length=20, unique=True, blank=True)
    is_public = models.BooleanField(default=False)
    image = models.ImageField(upload_to="tontines/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tontine"
        verbose_name_plural = "Tontines"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.memberships.filter(status=TontineMembership.Status.ACTIF).count()

    @property
    def is_full(self):
        return self.member_count >= self.max_members

    @property
    def can_start(self):
        return (
            self.member_count >= self.min_members
            and self.status == self.Status.EN_CREATION
        )

    def get_current_cycle(self):
        return self.cycles.filter(is_active=True).first()

    def get_total_collected(self):
        return sum(c.total_amount for c in self.cycles.all())


class TontineMembership(models.Model):
    class Role(models.TextChoices):
        TRESORIER = "tresorier", "Trésorier"
        MEMBRE = "membre", "Membre"

    class Status(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"
        QUITTE = "quitte", "Quitté"

    tontine = models.ForeignKey(
        Tontine, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBRE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.EN_ATTENTE
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_memberships",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Membre de Tontine"
        verbose_name_plural = "Membres de Tontine"
        unique_together = ("tontine", "user")
        ordering = ["role", "joined_at"]

    def __str__(self):
        return f"{self.user} - {self.tontine} ({self.get_role_display()})"

    @property
    def is_tresorier(self):
        return self.role == self.Role.TRESORIER

    @property
    def can_contribute(self):
        return (
            self.status == self.Status.ACTIF
            and self.tontine.status == Tontine.Status.ACTIVE
        )


class Cycle(models.Model):
    class Status(models.TextChoices):
        EN_COURS = "en_cours", "En cours"
        TERMINEE = "terminee", "Terminée"
        ANNULE = "annule", "Annulée"

    tontine = models.ForeignKey(
        Tontine, on_delete=models.CASCADE, related_name="cycles"
    )
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.EN_COURS
    )
    is_active = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    amount_per_member = models.DecimalField(max_digits=12, decimal_places=2)
    total_expected = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cycle"
        verbose_name_plural = "Cycles"
        ordering = ["-number"]
        unique_together = ("tontine", "number")

    def __str__(self):
        return f"{self.tontine.name} - {self.name}"

    @property
    def total_amount(self):
        return sum(c.amount for c in self.contributions.filter(status="valide"))

    @property
    def contribution_count(self):
        return self.contributions.filter(status="valide").count()

    @property
    def remaining_amount(self):
        return self.total_expected - self.total_amount

    @property
    def participation_rate(self):
        if self.total_expected == 0:
            return 0
        member_count = self.tontine.member_count
        if member_count == 0:
            return 0
        return (self.contribution_count / member_count) * 100
