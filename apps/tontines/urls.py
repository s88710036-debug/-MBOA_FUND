from django.urls import path
from .views import (
    DashboardView,
    TontineListView,
    TontineCreateView,
    TontineDetailView,
    TontineUpdateView,
    TontineDeleteView,
    JoinTontineView,
    JoinByCodeView,
    LeaveTontineView,
    ManageMembersView,
    MembershipActionView,
    CycleCreateView,
    ActivateTontineView,
)

app_name = "tontines"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("list/", TontineListView.as_view(), name="list"),
    path("create/", TontineCreateView.as_view(), name="create"),
    path("join/", JoinByCodeView.as_view(), name="join_by_code"),
    path("<uuid:uuid>/", TontineDetailView.as_view(), name="detail"),
    path("<uuid:uuid>/edit/", TontineUpdateView.as_view(), name="edit"),
    path("<uuid:uuid>/delete/", TontineDeleteView.as_view(), name="delete"),
    path("<uuid:uuid>/join/", JoinTontineView.as_view(), name="join"),
    path("<uuid:uuid>/leave/", LeaveTontineView.as_view(), name="leave"),
    path("<uuid:uuid>/members/", ManageMembersView.as_view(), name="manage_members"),
    path(
        "<uuid:uuid>/members/action/",
        MembershipActionView.as_view(),
        name="member_action",
    ),
    path("<uuid:uuid>/cycle/create/", CycleCreateView.as_view(), name="cycle_create"),
    path("<uuid:uuid>/activate/", ActivateTontineView.as_view(), name="activate"),
]
