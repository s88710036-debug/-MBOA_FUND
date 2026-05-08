from django.urls import path
from .views import (
    ContributionListView,
    ContributionCreateView,
    ContributionDetailView,
    TresorierContributionListView,
    ValidateContributionView,
    BulkValidationView,
    CycleContributionsView,
    ContributionStatsView,
)

app_name = "contributions"

urlpatterns = [
    path("", ContributionListView.as_view(), name="list"),
    path("create/<uuid:cycle_uuid>/", ContributionCreateView.as_view(), name="create"),
    path("<uuid:uuid>/", ContributionDetailView.as_view(), name="detail"),
    path(
        "tresorier/<uuid:tontine_uuid>/",
        TresorierContributionListView.as_view(),
        name="tresorier_list",
    ),
    path("<uuid:uuid>/validate/", ValidateContributionView.as_view(), name="validate"),
    path(
        "tresorier/<uuid:tontine_uuid>/bulk/",
        BulkValidationView.as_view(),
        name="bulk_validate",
    ),
    path(
        "cycle/<uuid:cycle_uuid>/",
        CycleContributionsView.as_view(),
        name="cycle_detail",
    ),
    path("stats/<uuid:tontine_uuid>/", ContributionStatsView.as_view(), name="stats"),
]
