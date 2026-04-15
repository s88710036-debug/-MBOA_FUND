from django.db import models
from django.conf import settings


class Report(models.Model):
    class ReportType(models.TextChoices):
        CONTRIBUTIONS = "contributions", "Rapport des cotisations"
        DRAWS = "draws", "Rapport des tirages"
        MEMBERS = "members", "Rapport des membres"
        FINANCIAL = "financial", "Rapport financier"
        CYCLE = "cycle", "Rapport de cycle"
        GENERAL = "general", "Rapport général"

    class Status(models.TextChoices):
        GENERATING = "generating", "En cours de génération"
        READY = "ready", "Prêt"
        FAILED = "failed", "Échoué"

    class Format(models.TextChoices):
        HTML = "html", "HTML"
        PDF = "pdf", "PDF"
        EXCEL = "excel", "Excel"
        CSV = "csv", "CSV"

    tontine = models.ForeignKey(
        "tontines.Tontine", on_delete=models.CASCADE, related_name="reports"
    )

    report_type = models.CharField(max_length=30, choices=ReportType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    format = models.CharField(
        max_length=10, choices=Format.choices, default=Format.HTML
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.GENERATING
    )

    file_path = models.FileField(upload_to="reports/", blank=True, null=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports",
    )

    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)

    error_message = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class MonthlyReport(models.Model):
    tontine = models.ForeignKey(
        "tontines.Tontine", on_delete=models.CASCADE, related_name="monthly_reports"
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()

    total_contributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    total_contributions_count = models.PositiveIntegerField(default=0)
    validated_contributions = models.PositiveIntegerField(default=0)
    rejected_contributions = models.PositiveIntegerField(default=0)

    total_payouts = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_payouts_count = models.PositiveIntegerField(default=0)

    total_draws = models.PositiveIntegerField(default=0)
    total_winners = models.PositiveIntegerField(default=0)
    total_winnings = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    new_members = models.PositiveIntegerField(default=0)
    left_members = models.PositiveIntegerField(default=0)

    participation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rapport mensuel"
        verbose_name_plural = "Rapports mensuels"
        unique_together = ("tontine", "year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        from calendar import month_name

        return f"{self.tontine.name} - {month_name[self.month]} {self.year}"
