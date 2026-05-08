"""
Configuration de l'interface admin pour les paiements.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages

from .models import TransactionLog, SMSNotificationLog, PaymentDashboardCache


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    """
    Interface admin pour le journal des transactions.

    Permet de:
    - Voir toutes les transactions
    - Filtrer par provider, statut, date
    - Relancer les transactions échouées
    - Exporter en CSV
    """

    list_display = [
        "transaction_id_short",
        "provider_badge",
        "amount_display",
        "status_badge",
        "user_link",
        "created_at",
        "retry_count",
    ]

    list_filter = [
        "provider",
        "status",
        "created_at",
    ]

    search_fields = [
        "transaction_id",
        "external_transaction_id",
        "user__email",
        "user__first_name",
        "user__last_name",
        "tontine__name",
    ]

    readonly_fields = [
        "transaction_id",
        "created_at",
        "updated_at",
        "completed_at",
        "request_data",
        "response_data",
        "callback_data",
    ]

    fieldsets = [
        (
            "Informations",
            {
                "fields": [
                    ("transaction_id", "provider"),
                    ("amount", "currency"),
                    ("status", "retry_count"),
                ]
            },
        ),
        (
            "Relations",
            {
                "fields": [
                    ("user", "tontine"),
                    "contribution",
                ]
            },
        ),
        (
            "Références Externes",
            {
                "fields": [
                    "external_transaction_id",
                    "payment_url",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Données Techniques",
            {
                "fields": [
                    "request_data",
                    "response_data",
                    "callback_data",
                    "error_message",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    ("created_at", "updated_at", "completed_at"),
                    "next_retry_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    actions = [
        "retry_failed_transactions",
        "mark_as_successful",
    ]

    def transaction_id_short(self, obj):
        """Affiche un ID tronqué."""
        return format_html(
            '<code title="{}">{}</code>',
            obj.transaction_id,
            obj.transaction_id[:20] + "...",
        )

    transaction_id_short.short_description = "ID Transaction"
    transaction_id_short.admin_order_field = "transaction_id"

    def provider_badge(self, obj):
        """Affiche le provider avec un badge coloré."""
        colors = {
            "orange_money": "warning",
            "wave": "info",
            "stripe": "primary",
        }
        color = colors.get(obj.provider, "secondary")
        display = obj.get_provider_display()
        return format_html('<span class="badge bg-{}">{}</span>', color, display)

    provider_badge.short_description = "Provider"
    provider_badge.admin_order_field = "provider"

    def amount_display(self, obj):
        """Affiche le montant formaté."""
        return format_html(
            '<strong class="text-success">{} XAF</strong>', f"{obj.amount:,.0f}"
        )

    amount_display.short_description = "Montant"
    amount_display.admin_order_field = "amount"

    def status_badge(self, obj):
        """Affiche le statut avec un badge coloré."""
        colors = {
            "success": "success",
            "pending": "warning",
            "processing": "info",
            "failed": "danger",
            "cancelled": "secondary",
            "refunded": "dark",
            "retry_scheduled": "info",
            "max_retries_exceeded": "danger",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>', color, obj.get_status_display()
        )

    status_badge.short_description = "Statut"
    status_badge.admin_order_field = "status"

    def user_link(self, obj):
        """Affiche un lien vers l'utilisateur."""
        if obj.user:
            url = reverse("admin:accounts_user_change", args=[obj.user.id])
            return format_html(
                '<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.email
            )
        return "-"

    user_link.short_description = "Utilisateur"
    user_link.admin_order_field = "user"

    def retry_failed_transactions(self, request, queryset):
        """Relance les transactions sélectionnées."""
        count = 0
        for tx in queryset.filter(status="failed", can_retry=True):
            tx.schedule_retry()
            count += 1

        self.message_user(request, f"{count} transactions planifiées pour retry.")

    retry_failed_transactions.short_description = "Relancer les transactions échouées"

    def mark_as_successful(self, request, queryset):
        """Marque les transactions comme réussies."""
        count = 0
        for tx in queryset:
            tx.mark_success({"manual": True, "admin": request.user.id})
            count += 1

        self.message_user(request, f"{count} transactions marquée(s) comme réussie(s).")

    mark_as_successful.short_description = "Marquer comme réussi"


@admin.register(SMSNotificationLog)
class SMSNotificationLogAdmin(admin.ModelAdmin):
    """
    Interface admin pour les logs SMS.
    """

    list_display = [
        "phone_number",
        "provider_badge",
        "status_badge",
        "notification_type",
        "created_at",
        "sent_at",
    ]

    list_filter = [
        "provider",
        "status",
        "created_at",
    ]

    search_fields = [
        "phone_number",
        "user__email",
        "message",
    ]

    readonly_fields = [
        "created_at",
        "sent_at",
        "response_data",
    ]

    def provider_badge(self, obj):
        colors = {"africas_talking": "info", "orange": "warning"}
        color = colors.get(obj.provider, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>', color, obj.get_provider_display()
        )

    provider_badge.short_description = "Provider"

    def status_badge(self, obj):
        colors = {
            "sent": "success",
            "pending": "warning",
            "failed": "danger",
            "delivered": "info",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>', color, obj.get_status_display()
        )

    status_badge.short_description = "Statut"


@admin.register(PaymentDashboardCache)
class PaymentDashboardCacheAdmin(admin.ModelAdmin):
    """
    Interface admin pour le dashboard financier.
    """

    list_display = [
        "date",
        "total_transactions",
        "total_amount_display",
        "updated_at",
    ]

    readonly_fields = ["date", "updated_at"]

    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.0f} XAF"

    total_amount_display.short_description = "Montant Total"
