from django.test import TestCase
from apps.notifications.services_module import NotificationService


class NotificationServiceTest(TestCase):
    def setUp(self):
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )

    def test_create_notification(self):
        notification = NotificationService.create_notification(
            user=self.user,
            title="Test",
            message="Test message",
        )
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "Test")

    def test_create_notification_with_type(self):
        from apps.notifications.models import Notification

        notification = NotificationService.create_notification(
            user=self.user,
            title="Success",
            message="Operation successful",
            notification_type=Notification.NotificationType.SUCCESS,
        )
        self.assertEqual(
            notification.notification_type, Notification.NotificationType.SUCCESS
        )

    def test_create_notification_with_priority(self):
        from apps.notifications.models import Notification

        notification = NotificationService.create_notification(
            user=self.user,
            title="Important",
            message="High priority message",
            priority=Notification.Priority.HIGH,
        )
        self.assertEqual(notification.priority, Notification.Priority.HIGH)

    def test_get_user_notifications(self):
        from apps.notifications.models import Notification

        for i in range(5):
            NotificationService.create_notification(
                user=self.user,
                title=f"Notification {i}",
                message=f"Message {i}",
            )
        notifications = NotificationService.get_user_notifications(self.user)
        self.assertEqual(notifications.count(), 5)

    def test_get_unread_notifications(self):
        from apps.notifications.models import Notification

        NotificationService.create_notification(
            user=self.user,
            title="Unread",
            message="Unread message",
        )
        NotificationService.create_notification(
            user=self.user,
            title="Read",
            message="Read message",
        )
        unread = NotificationService.get_unread_notifications(self.user)
        self.assertEqual(unread.count(), 2)

    def test_mark_as_read(self):
        from apps.notifications.models import Notification

        notification = NotificationService.create_notification(
            user=self.user,
            title="To Mark",
            message="Message",
        )
        self.assertFalse(notification.is_read)
        NotificationService.mark_as_read(notification)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_all_as_read(self):
        from apps.notifications.models import Notification

        for i in range(3):
            NotificationService.create_notification(
                user=self.user,
                title=f"Notification {i}",
                message=f"Message {i}",
            )
        NotificationService.mark_all_as_read(self.user)
        unread = NotificationService.get_unread_notifications(self.user)
        self.assertEqual(unread.count(), 0)

    def test_delete_old_notifications(self):
        from apps.notifications.models import Notification

        notification = NotificationService.create_notification(
            user=self.user,
            title="Old",
            message="Message",
        )
        deleted = NotificationService.delete_old_notifications(days=0)
        self.assertGreaterEqual(deleted, 1)
