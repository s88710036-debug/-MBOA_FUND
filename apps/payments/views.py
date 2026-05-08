"""
Vues pour les paiements.

Ce module contient toutes les vues nécessaires pour:
- Le checkout de paiement
- Les webhooks des providers
- La simulation en mode sandbox
- L'historique des transactions
"""

import json
import logging
from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, FormView, View
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.contributions.models import Contribution

from .models import TransactionLog
from .forms import PaymentMethodForm, PaymentSimulationForm
from .services import PaymentServiceFactory

logger = logging.getLogger(__name__)


class PaymentCheckoutView(LoginRequiredMixin, TemplateView):
    """
    Vue pour la page de checkout de paiement.

    Cette vue affiche le récapitulatif de la cotisation
    et permet de sélectionner la méthode de paiement.
    """

    template_name = "payments/payment_checkout.html"

    def get_contribution(self):
        """Récupère la contribution à payer."""
        contribution_uuid = self.kwargs.get("contribution_uuid")
        return get_object_or_404(
            Contribution.objects.select_related("tontine", "cycle", "user"),
            uuid=contribution_uuid,
        )

    def get_context_data(self, **kwargs):
        """Ajoute les données de contexte pour le template."""
        context = super().get_context_data(**kwargs)

        contribution = self.get_contribution()

        if contribution.user != self.request.user:
            messages.error(
                self.request, "Vous ne pouvez pas payer pour un autre membre."
            )
            return context

        if contribution.is_paid:
            messages.warning(self.request, "Cette cotisation a déjà été validée.")
            return context

        context["contribution"] = contribution
        context["payment_form"] = PaymentMethodForm(
            initial={"phone_number": self.request.user.phone}
        )
        context["stripe_public_key"] = settings.STRIPE_SETTINGS.get("PUBLIC_KEY", "")

        return context

    def post(self, request, *args, **kwargs):
        """Traite le formulaire de sélection de paiement."""
        contribution = self.get_contribution()
        form = PaymentMethodForm(request.POST)

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(payment_form=form))

        payment_method = form.cleaned_data["payment_method"]
        phone_number = form.cleaned_data.get("phone_number", "")

        try:
            service = PaymentServiceFactory.get_service(payment_method)

            response = service.create_payment(
                amount=contribution.amount,
                phone=phone_number,
                reference=f"COT-{contribution.uuid}",
                user_id=request.user.id,
                metadata={
                    "contribution_uuid": str(contribution.uuid),
                    "tontine_name": contribution.tontine.name,
                    "cycle_name": contribution.cycle.name,
                },
            )

            if response.success:
                contribution.transaction_id = response.transaction_id
                contribution.payment_method = payment_method
                contribution.sender_phone = phone_number
                contribution.save()

                if settings.DEBUG and response.data.get("sandbox"):
                    return redirect(
                        "payments:sandbox_simulate",
                        transaction_id=response.transaction_id,
                    )

                if response.payment_url:
                    return redirect(response.payment_url)

                messages.success(request, "Paiement créé avec succès!")
                return redirect(
                    "payments:success", transaction_id=response.transaction_id
                )
            else:
                messages.error(
                    request,
                    f"Erreur lors de la création du paiement: {response.message}",
                )
                return self.render_to_response(self.get_context_data(payment_form=form))

        except Exception as e:
            logger.error(f"Payment creation error: {e}")
            messages.error(request, "Une erreur est survenue. Veuillez réessayer.")
            return self.render_to_response(self.get_context_data(payment_form=form))


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    """Vue pour la page de succès de paiement."""

    template_name = "payments/payment_success.html"

    def get_context_data(self, **kwargs):
        """Ajoute les données de contexte."""
        context = super().get_context_data(**kwargs)

        transaction_id = self.kwargs.get("transaction_id")

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
            context["transaction"] = transaction
        except TransactionLog.DoesNotExist:
            pass

        return context


class PaymentPendingView(LoginRequiredMixin, TemplateView):
    """Vue pour la page en attente de confirmation."""

    template_name = "payments/payment_pending.html"

    def get_context_data(self, **kwargs):
        """Ajoute les données de contexte."""
        context = super().get_context_data(**kwargs)

        transaction_id = self.kwargs.get("transaction_id")

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
            context["transaction"] = transaction
            context["poll_url"] = reverse("payments:status_json", args=[transaction_id])
        except TransactionLog.DoesNotExist:
            pass

        return context


class PaymentStatusView(LoginRequiredMixin, View):
    """Vue pour vérifier le statut d'une transaction (API JSON)."""

    def get(self, request, transaction_id):
        """Retourne le statut de la transaction en JSON."""
        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)

            if transaction.status in ["pending", "processing", "retry_scheduled"]:
                service = PaymentServiceFactory.get_service(transaction.provider)
                service.check_payment_status(transaction_id)
                transaction.refresh_from_db()

            return JsonResponse(
                {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "status": transaction.status,
                    "amount": str(transaction.amount),
                    "provider": transaction.provider,
                    "is_completed": transaction.is_completed,
                }
            )

        except TransactionLog.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Transaction non trouvée"}, status=404
            )


@method_decorator(csrf_exempt, name="dispatch")
class OrangeWebhookView(View):
    """Vue pour traiter les webhooks Orange Money."""

    def post(self, request):
        """Traite un webhook Orange Money."""
        try:
            data = json.loads(request.body)

            service = PaymentServiceFactory.get_service("orange_money")
            response = service.handle_webhook(data)

            return HttpResponse(
                "OK" if response.success else "Error",
                status=200 if response.success else 400,
            )

        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            logger.error(f"Orange webhook error: {e}")
            return HttpResponse("Error", status=500)


@method_decorator(csrf_exempt, name="dispatch")
class WaveWebhookView(View):
    """Vue pour traiter les webhooks Wave."""

    def post(self, request):
        """Traite un webhook Wave."""
        try:
            data = json.loads(request.body)

            service = PaymentServiceFactory.get_service("wave")
            response = service.handle_webhook(data)

            return HttpResponse(
                "OK" if response.success else "Error",
                status=200 if response.success else 400,
            )

        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            logger.error(f"Wave webhook error: {e}")
            return HttpResponse("Error", status=500)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    """Vue pour traiter les webhooks Stripe."""

    def post(self, request):
        """Traite un webhook Stripe."""
        try:
            data = json.loads(request.body)

            service = PaymentServiceFactory.get_service("stripe")
            response = service.handle_webhook(data)

            return HttpResponse(
                "OK" if response.success else "Error",
                status=200 if response.success else 400,
            )

        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)
        except Exception as e:
            logger.error(f"Stripe webhook error: {e}")
            return HttpResponse("Error", status=500)


class SandboxSimulateView(LoginRequiredMixin, FormView):
    """Vue pour simuler un paiement en mode sandbox."""

    template_name = "payments/sandbox_simulate.html"
    form_class = PaymentSimulationForm

    def get_transaction(self):
        """Récupère la transaction à simuler."""
        transaction_id = self.kwargs.get("transaction_id")
        return get_object_or_404(
            TransactionLog.objects.select_related("user", "contribution"),
            transaction_id=transaction_id,
        )

    def get_context_data(self, **kwargs):
        """Ajoute les données de contexte."""
        context = super().get_context_data(**kwargs)
        context["transaction"] = self.get_transaction()
        return context

    def form_valid(self, form):
        """Traite le formulaire de simulation."""
        transaction = self.get_transaction()
        simulate_result = form.cleaned_data["simulate_result"]

        if simulate_result == "success":
            transaction.mark_success(
                {
                    "sandbox": True,
                    "simulated_at": timezone.now().isoformat(),
                }
            )

            if transaction.contribution:
                transaction.contribution.status = Contribution.Status.VALIDE
                transaction.contribution.validated_at = timezone.now()
                transaction.contribution.save()

            messages.success(self.request, "Paiement simulé avec succès!")
            return redirect(
                "payments:success", transaction_id=transaction.transaction_id
            )

        else:
            transaction.mark_failed(
                error_message="Paiement simulé comme échoué",
                response_data={"sandbox": True},
            )

            messages.warning(self.request, "Paiement simulé comme échoué.")
            return redirect(
                "payments:pending", transaction_id=transaction.transaction_id
            )


class TransactionHistoryView(LoginRequiredMixin, ListView):
    """Vue pour afficher l'historique des transactions."""

    model = TransactionLog
    template_name = "payments/transaction_history.html"
    context_object_name = "transactions"
    paginate_by = 20

    def get_queryset(self):
        """Retourne les transactions de l'utilisateur."""
        queryset = TransactionLog.objects.filter(user=self.request.user)

        provider = self.request.GET.get("provider")
        if provider:
            queryset = queryset.filter(provider=provider)

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related("tontine", "contribution")

    def get_context_data(self, **kwargs):
        """Ajoute les données de contexte."""
        context = super().get_context_data(**kwargs)

        transactions = self.get_queryset()
        context["total_amount"] = sum(
            t.amount for t in transactions.filter(status="success")
        )
        context["pending_count"] = transactions.filter(
            status__in=["pending", "processing"]
        ).count()

        return context


class SandboxSimulateSuccessView(LoginRequiredMixin, View):
    """Vue API pour simuler un succès de paiement (pour HTMX)."""

    def post(self, request, transaction_id):
        """Simule un succès pour la transaction donnée."""
        if not settings.DEBUG:
            return HttpResponseForbidden("Disponible uniquement en mode debug")

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
        except TransactionLog.DoesNotExist:
            return JsonResponse({"success": False, "error": "Transaction non trouvée"})

        transaction.mark_success(
            {
                "sandbox": True,
                "simulated_at": timezone.now().isoformat(),
            }
        )

        if transaction.contribution:
            transaction.contribution.status = Contribution.Status.VALIDE
            transaction.contribution.validated_at = timezone.now()
            transaction.contribution.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Paiement confirmé",
                "transaction_id": transaction_id,
            }
        )


class SandboxSimulateFailureView(LoginRequiredMixin, View):
    """Vue API pour simuler un échec de paiement (pour HTMX)."""

    def post(self, request, transaction_id):
        """Simule un échec pour la transaction donnée."""
        if not settings.DEBUG:
            return HttpResponseForbidden("Disponible uniquement en mode debug")

        try:
            transaction = TransactionLog.objects.get(transaction_id=transaction_id)
        except TransactionLog.DoesNotExist:
            return JsonResponse({"success": False, "error": "Transaction non trouvée"})

        transaction.mark_failed(
            error_message="Paiement simulé comme échoué",
            response_data={"sandbox": True},
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Échec simulé",
                "transaction_id": transaction_id,
            }
        )
