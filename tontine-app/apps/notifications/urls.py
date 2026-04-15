from django.urls import path
from .views import (
    NotificationListView,
    MarkAsReadView,
    MarkAllAsReadView,
    NotificationSettingsView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("<int:notification_id>/read/", MarkAsReadView.as_view(), name="mark_read"),
    path("read-all/", MarkAllAsReadView.as_view(), name="mark_all_read"),
    path("settings/", NotificationSettingsView.as_view(), name="settings"),
]
