from django.urls import path
from .views import (
    ReportDashboardView,
    ContributionReportView,
    MemberReportView,
    FinancialReportView,
    ExportReportView,
)

app_name = "reports"

urlpatterns = [
    path("", ReportDashboardView.as_view(), name="dashboard"),
    path("<uuid:tontine_uuid>/", ReportDashboardView.as_view(), name="dashboard"),
    path(
        "<uuid:tontine_uuid>/contributions/",
        ContributionReportView.as_view(),
        name="contributions",
    ),
    path("<uuid:tontine_uuid>/members/", MemberReportView.as_view(), name="members"),
    path(
        "<uuid:tontine_uuid>/financial/",
        FinancialReportView.as_view(),
        name="financial",
    ),
    path(
        "<uuid:tontine_uuid>/export/<str:report_type>/",
        ExportReportView.as_view(),
        name="export",
    ),
]
