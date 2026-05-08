from django.contrib import admin
from .models import Notification, EmailNotification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "title",
        "notification_type",
        "priority",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "priority", "is_read", "created_at")
    search_fields = ("user__username", "title", "message")


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "subject", "status", "sent_at", "created_at")
    list_filter = ("status", "created_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email_enabled",
        "push_enabled",
        "in_app_enabled",
        "updated_at",
    )
