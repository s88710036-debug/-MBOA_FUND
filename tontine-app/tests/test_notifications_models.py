from django.test import TestCase
from apps.accounts.models import User
from apps.notifications.models import (
    Notification,
    EmailNotification,
    NotificationPreference,
)


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )

    def test_notification_creation(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test message",
            notification_type=Notification.NotificationType.INFO,
        )
        self.assertEqual(notification.title, "Test Notification")
        self.assertFalse(notification.is_read)

    def test_notification_str(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test message",
        )
        self.assertIn("Test Notification", str(notification))

    def test_notification_type_choices(self):
        self.assertIn(
            Notification.NotificationType.INFO, Notification.NotificationType.values
        )
        self.assertIn(
            Notification.NotificationType.SUCCESS, Notification.NotificationType.values
        )
        self.assertIn(
            Notification.NotificationType.WARNING, Notification.NotificationType.values
        )
        self.assertIn(
            Notification.NotificationType.ERROR, Notification.NotificationType.values
        )

    def test_priority_choices(self):
        self.assertIn(Notification.Priority.LOW, Notification.Priority.values)
        self.assertIn(Notification.Priority.NORMAL, Notification.Priority.values)
        self.assertIn(Notification.Priority.HIGH, Notification.Priority.values)

    def test_mark_as_read(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test message",
        )
        self.assertFalse(notification.is_read)
        notification.is_read = True
        notification.save()
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)


class EmailNotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test message",
        )

    def test_email_notification_creation(self):
        email = EmailNotification.objects.create(
            notification=self.notification,
            recipient=self.user.email,
            subject="Test Subject",
        )
        self.assertEqual(email.status, EmailNotification.Status.PENDING)

    def test_email_notification_str(self):
        email = EmailNotification.objects.create(
            notification=self.notification,
            recipient=self.user.email,
            subject="Test Subject",
        )
        self.assertIn(self.user.email, str(email))


class NotificationPreferenceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
        )
        self.preference = NotificationPreference.objects.create(user=self.user)

    def test_preference_creation(self):
        self.assertTrue(self.preference.email_enabled)
        self.assertTrue(self.preference.push_enabled)
        self.assertTrue(self.preference.in_app_enabled)

    def test_preference_str(self):
        expected = f"Préférences de {self.user}"
        self.assertEqual(str(self.preference), expected)

    def test_preference_one_to_one(self):
        with self.assertRaises(Exception):
            NotificationPreference.objects.create(user=self.user)

    def test_default_notification_types(self):
        self.assertTrue(self.preference.notify_contributions)
        self.assertTrue(self.preference.notify_draws)
        self.assertTrue(self.preference.notify_members)
        self.assertTrue(self.preference.notify_system)
