"""
Services pour les notifications.
"""

from django.utils import timezone
from datetime import timedelta
from apps.notifications.models import (
    Notification,
    EmailNotification,
    NotificationPreference,
)


class NotificationService:
    @staticmethod
    def create_notification(
        user,
        title,
        message,
        notification_type=Notification.NotificationType.INFO,
        priority=Notification.Priority.NORMAL,
        link="",
        icon="",
    ):
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            link=link,
            icon=icon,
        )
        return notification

    @staticmethod
    def get_user_notifications(user, limit=None):
        qs = Notification.objects.filter(user=user)
        if limit:
            return qs[:limit]
        return qs

    @staticmethod
    def get_unread_notifications(user):
        return Notification.objects.filter(user=user, is_read=False)

    @staticmethod
    def mark_as_read(notification):
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return notification

    @staticmethod
    def mark_all_as_read(user):
        notifications = Notification.objects.filter(user=user, is_read=False)
        count = notifications.count()
        notifications.update(is_read=True, read_at=timezone.now())
        return count

    @staticmethod
    def delete_old_notifications(days=30):
        cutoff = timezone.now() - timedelta(days=days)
        old_notifications = Notification.objects.filter(created_at__lt=cutoff)
        count = old_notifications.count()
        old_notifications.delete()
        return count

    @staticmethod
    def send_email_notification(notification, recipient, subject):
        email = EmailNotification.objects.create(
            notification=notification,
            recipient=recipient,
            subject=subject,
        )
        return email

    @staticmethod
    def get_unread_count(user):
        return Notification.objects.filter(user=user, is_read=False).count()
