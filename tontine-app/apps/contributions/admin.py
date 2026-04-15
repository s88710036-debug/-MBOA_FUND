from django.contrib import admin
from .models import Contribution, MobileMoneyTransaction, PaymentRequest, Payout


class TransactionInline(admin.TabularInline):
    model = MobileMoneyTransaction
    extra = 0
    readonly_fields = ("created_at", "external_transaction_id", "status")


class ContributionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "tontine",
        "cycle",
        "amount",
        "payment_method",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_method", "tontine", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "reference_number",
        "transaction_id",
    )
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = [TransactionInline]


class MobileMoneyTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "contribution",
        "provider",
        "amount",
        "sender_phone",
        "status",
        "created_at",
    )
    list_filter = ("provider", "status", "created_at")
    search_fields = (
        "external_transaction_id",
        "merchant_transaction_id",
        "sender_phone",
    )


class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "contribution",
        "payment_method",
        "amount",
        "status",
        "expires_at",
        "created_at",
    )
    list_filter = ("payment_method", "status", "created_at")
    search_fields = ("payment_token",)


class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "tontine",
        "amount",
        "payment_method",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_method", "tontine", "created_at")
    search_fields = ("recipient__username", "transaction_id")


admin.site.register(Contribution, ContributionAdmin)
admin.site.register(MobileMoneyTransaction, MobileMoneyTransactionAdmin)
admin.site.register(PaymentRequest, PaymentRequestAdmin)
admin.site.register(Payout, PayoutAdmin)
