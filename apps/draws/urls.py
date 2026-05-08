from django.urls import path
from .views import (
    DrawListView,
    DrawDetailView,
    DrawCreateView,
    PerformDrawView,
    UpdateWinnerStatusView,
    CycleDrawsView,
)

app_name = "draws"

urlpatterns = [
    path("", DrawListView.as_view(), name="list"),
    path("<uuid:uuid>/", DrawDetailView.as_view(), name="detail"),
    path("<uuid:uuid>/perform/", PerformDrawView.as_view(), name="perform"),
    path("winner/<uuid:uuid>/", UpdateWinnerStatusView.as_view(), name="winner_update"),
    path("cycle/<uuid:cycle_uuid>/", CycleDrawsView.as_view(), name="cycle_draws"),
    path("cycle/<uuid:cycle_uuid>/create/", DrawCreateView.as_view(), name="create"),
]
