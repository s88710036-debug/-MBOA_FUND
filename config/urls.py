from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("tontines/", include("apps.tontines.urls")),
    path("contributions/", include("apps.contributions.urls")),
    path("tirages/", include("apps.draws.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("chat/", include("apps.chat.urls")),
    path("rapports/", include("apps.reports.urls")),
    path("payments/", include("apps.payments.urls")),
]
