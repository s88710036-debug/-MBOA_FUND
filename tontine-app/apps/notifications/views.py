from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, View, UpdateView
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from .models import Notification, NotificationPreference


def notifications(request):
    if request.user.is_authenticated:
        return {
            "notifications": Notification.objects.filter(
                user=request.user, is_read=False
            )[:5],
            "unread_count": Notification.objects.filter(
                user=request.user, is_read=False
            ).count(),
        }
    return {}


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)

        filter_type = self.request.GET.get("filter")
        if filter_type == "unread":
            queryset = queryset.filter(is_read=False)
        elif filter_type == "read":
            queryset = queryset.filter(is_read=True)

        return queryset


class MarkAsReadView(LoginRequiredMixin, View):
    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification, id=notification_id, user=request.user
        )
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        if request.htmx:
            return JsonResponse({"status": "ok"})

        return JsonResponse(
            {
                "status": "ok",
                "unread_count": Notification.objects.filter(
                    user=request.user, is_read=False
                ).count(),
            }
        )


class MarkAllAsReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

        if request.htmx:
            return JsonResponse({"status": "ok", "unread_count": 0})

        return JsonResponse({"status": "ok"})


class NotificationSettingsView(LoginRequiredMixin, UpdateView):
    model = NotificationPreference
    template_name = "notifications/notification_settings.html"
    fields = [
        "email_enabled",
        "push_enabled",
        "in_app_enabled",
        "notify_contributions",
        "notify_draws",
        "notify_members",
        "notify_system",
        "notify_on_new_cycle",
        "notify_on_contribution",
        "notify_on_draw",
        "notify_on_payment",
        "quiet_hours_start",
        "quiet_hours_end",
    ]

    def get_object(self):
        pref, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return pref

    def form_valid(self, form):
        from django.contrib import messages

        messages.success(self.request, "Préférences de notification enregistrées.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.META.get("HTTP_REFERER", "/")
