"""
Configuration des URLs pour les paiements.
"""

from django.urls import path
from .views import (
    PaymentCheckoutView,
    PaymentSuccessView,
    PaymentPendingView,
    PaymentStatusView,
    OrangeWebhookView,
    WaveWebhookView,
    StripeWebhookView,
    SandboxSimulateView,
    SandboxSimulateSuccessView,
    SandboxSimulateFailureView,
    TransactionHistoryView,
)

app_name = "payments"

urlpatterns = [
    # Checkout
    path(
        "checkout/<uuid:contribution_uuid>/",
        PaymentCheckoutView.as_view(),
        name="checkout",
    ),
    # Pages de résultat
    path("success/<str:transaction_id>/", PaymentSuccessView.as_view(), name="success"),
    path("pending/<str:transaction_id>/", PaymentPendingView.as_view(), name="pending"),
    # Statut (API JSON)
    path("status/<str:transaction_id>/", PaymentStatusView.as_view(), name="status"),
    path(
        "status/<str:transaction_id>/json/",
        PaymentStatusView.as_view(),
        name="status_json",
    ),
    # Webhooks
    path("webhooks/orange/", OrangeWebhookView.as_view(), name="webhook_orange"),
    path("webhooks/wave/", WaveWebhookView.as_view(), name="webhook_wave"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="webhook_stripe"),
    # Sandbox (mode debug uniquement)
    path(
        "sandbox/simulate/<str:transaction_id>/",
        SandboxSimulateView.as_view(),
        name="sandbox_simulate",
    ),
    path(
        "sandbox/simulate-success/<str:transaction_id>/",
        SandboxSimulateSuccessView.as_view(),
        name="sandbox_simulate_success",
    ),
    path(
        "sandbox/simulate-failure/<str:transaction_id>/",
        SandboxSimulateFailureView.as_view(),
        name="sandbox_simulate_failure",
    ),
    # Historique
    path("history/", TransactionHistoryView.as_view(), name="history"),
]
