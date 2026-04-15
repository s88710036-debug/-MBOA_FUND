from django.db import models
from django.conf import settings


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = "info", "Information"
        SUCCESS = "success", "Succès"
        WARNING = "warning", "Avertissement"
        ERROR = "error", "Erreur"

    class Priority(models.TextChoices):
        LOW = "low", "Basse"
        NORMAL = "normal", "Normale"
        HIGH = "high", "Haute"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices, default=NotificationType.INFO
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )

    link = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=50, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    email_sent = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"

    @property
    def time_since(self):
        from django.utils import timezone
        from django.utils.timesince import timesince

        return timesince(self.created_at, timezone.now())


class EmailNotification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        SENT = "sent", "Envoyé"
        FAILED = "failed", "Échoué"

    notification = models.OneToOneField(
        Notification, on_delete=models.CASCADE, related_name="email_record"
    )
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification email"
        verbose_name_plural = "Notifications email"

    def __str__(self):
        return f"Email à {self.recipient} - {self.status}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)

    notify_contributions = models.BooleanField(default=True)
    notify_draws = models.BooleanField(default=True)
    notify_members = models.BooleanField(default=True)
    notify_system = models.BooleanField(default=True)

    notify_on_new_cycle = models.BooleanField(default=True)
    notify_on_contribution = models.BooleanField(default=True)
    notify_on_draw = models.BooleanField(default=True)
    notify_on_payment = models.BooleanField(default=True)

    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"

    def __str__(self):
        return f"Préférences de {self.user}"
