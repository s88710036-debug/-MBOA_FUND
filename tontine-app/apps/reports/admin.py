from django.contrib import admin
from .models import Report, MonthlyReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "tontine",
        "report_type",
        "format",
        "status",
        "generated_by",
        "created_at",
    )
    list_filter = ("report_type", "format", "status", "tontine")


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = (
        "tontine",
        "year",
        "month",
        "total_contributions",
        "total_payouts",
        "participation_rate",
    )
    list_filter = ("year", "month", "tontine")
