import uuid
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, View
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from apps.tontines.models import Tontine, TontineMembership, Cycle
from apps.notifications.models import Notification
from .models import Contribution, MobileMoneyTransaction, PaymentRequest, Payout
from .forms import (
    ContributionForm,
    ManualContributionForm,
    ContributionValidationForm,
    BulkValidationForm,
)


class ContributionListView(LoginRequiredMixin, ListView):
    model = Contribution
    template_name = "contributions/contribution_list.html"
    context_object_name = "contributions"
    paginate_by = 20

    def get_queryset(self):
        queryset = Contribution.objects.filter(user=self.request.user)

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        tontine_slug = self.request.GET.get("tontine")
        if tontine_slug:
            queryset = queryset.filter(tontine__uuid=tontine_slug)

        return queryset.select_related("tontine", "cycle", "user")


class ContributionCreateView(LoginRequiredMixin, CreateView):
    model = Contribution
    form_class = ContributionForm
    template_name = "contributions/contribution_form.html"

    def get_cycle(self):
        cycle_uuid = self.kwargs.get("cycle_uuid")
        return get_object_or_404(Cycle, uuid=cycle_uuid)

    def get(self, request, *args, **kwargs):
        cycle = self.get_cycle()

        try:
            membership = TontineMembership.objects.get(
                tontine=cycle.tontine, user=request.user, status="actif"
            )
        except TontineMembership.DoesNotExist:
            messages.error(request, "Vous n'êtes pas membre actif de cette tontine.")
            return redirect("tontines:detail", uuid=cycle.tontine.uuid)

        existing = Contribution.objects.filter(user=request.user, cycle=cycle).exists()
        if existing:
            messages.warning(
                request, "Vous avez déjà soumis une cotisation pour ce cycle."
            )
            return redirect("contributions:list")

        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cycle"] = self.get_cycle()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        cycle = self.get_cycle()
        form.instance.user = self.request.user
        form.instance.cycle = cycle
        form.instance.tontine = cycle.tontine
        form.instance.status = "en_attente"

        response = super().form_valid(form)

        Notification.objects.create(
            user=self.request.user,
            title="Cotisation soumise",
            message=f"Votre cotisation de {form.instance.amount} XAF pour {cycle.name} a été soumise.",
            notification_type="success",
        )

        tresoriers = TontineMembership.objects.filter(
            tontine=cycle.tontine, role="tresorier", status="actif"
        ).select_related("user")

        for m in tresoriers:
            Notification.objects.create(
                user=m.user,
                title="Nouvelle cotisation",
                message=f"{self.request.user.get_full_name()} a soumis une cotisation de {form.instance.amount} XAF.",
                notification_type="info",
            )

        messages.success(self.request, "Cotisation soumise avec succès !")
        return redirect("payments:checkout", contribution_uuid=form.instance.uuid)

    def get_success_url(self):
        return reverse(
            "payments:checkout", kwargs={"contribution_uuid": self.object.uuid}
        )


class ContributionDetailView(LoginRequiredMixin, TemplateView):
    template_name = "contributions/contribution_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contribution"] = get_object_or_404(
            Contribution.objects.select_related(
                "tontine", "cycle", "user", "validated_by"
            ),
            uuid=kwargs.get("uuid"),
        )
        return context


class TresorierContributionListView(LoginRequiredMixin, ListView):
    model = Contribution
    template_name = "contributions/tresorier_contributions.html"
    context_object_name = "contributions"
    paginate_by = 20

    def get_queryset(self):
        tontine_uuid = self.kwargs.get("tontine_uuid")
        queryset = Contribution.objects.filter(tontine__uuid=tontine_uuid)

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related("tontine", "cycle", "user").order_by(
            "-created_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tontine"] = get_object_or_404(
            Tontine, uuid=self.kwargs.get("tontine_uuid")
        )
        return context


class ValidateContributionView(LoginRequiredMixin, View):
    def post(self, request, uuid):
        contribution = get_object_or_404(Contribution, uuid=uuid)

        try:
            membership = TontineMembership.objects.get(
                tontine=contribution.tontine,
                user=request.user,
                role="tresorier",
                status="actif",
            )
        except TontineMembership.DoesNotExist:
            return HttpResponseForbidden("Vous n'êtes pas autorisé à valider.")

        action = request.POST.get("action")
        reason = request.POST.get("rejection_reason", "")

        if action == "validate":
            contribution.status = "valide"
            contribution.validated_by = request.user
            contribution.validated_at = timezone.now()
            contribution.save()

            Notification.objects.create(
                user=contribution.user,
                title="Cotisation validée",
                message=f"Votre cotisation de {contribution.amount} XAF a été validée.",
                notification_type="success",
            )
            messages.success(request, "Cotisation validée avec succès.")

        elif action == "reject":
            contribution.status = "rejete"
            contribution.rejected_reason = reason
            contribution.save()

            Notification.objects.create(
                user=contribution.user,
                title="Cotisation rejetée",
                message=f"Votre cotisation a été rejetée. Raison: {reason}",
                notification_type="error",
            )
            messages.warning(request, "Cotisation rejetée.")

        return redirect(
            "contributions:tresorier_list", tontine_uuid=contribution.tontine.uuid
        )


class BulkValidationView(LoginRequiredMixin, View):
    def post(self, request, tontine_uuid):
        tontine = get_object_or_404(Tontine, uuid=tontine_uuid)

        try:
            membership = TontineMembership.objects.get(
                tontine=tontine, user=request.user, role="tresorier", status="actif"
            )
        except TontineMembership.DoesNotExist:
            return HttpResponseForbidden("Vous n'êtes pas autorisé.")

        form = BulkValidationForm(request.POST)
        if form.is_valid():
            ids = form.cleaned_data["contribution_ids"].split(",")
            action = form.cleaned_data["action"]
            reason = form.cleaned_data.get("rejection_reason", "")

            contributions = Contribution.objects.filter(id__in=ids, tontine=tontine)

            if action == "validate_all":
                for c in contributions:
                    c.status = "valide"
                    c.validated_by = request.user
                    c.validated_at = timezone.now()
                    c.save()

                    Notification.objects.create(
                        user=c.user,
                        title="Cotisation validée",
                        message=f"Votre cotisation de {c.amount} XAF a été validée.",
                        notification_type="success",
                    )
                messages.success(
                    request, f"{contributions.count()} cotisations validées."
                )

            elif action == "reject_all":
                for c in contributions:
                    c.status = "rejete"
                    c.rejected_reason = reason
                    c.save()

                    Notification.objects.create(
                        user=c.user,
                        title="Cotisation rejetée",
                        message=f"Votre cotisation a été rejetée.",
                        notification_type="error",
                    )
                messages.warning(
                    request, f"{contributions.count()} cotisations rejetées."
                )

        return redirect("contributions:tresorier_list", tontine_uuid=tontine_uuid)


class CycleContributionsView(LoginRequiredMixin, TemplateView):
    template_name = "contributions/cycle_contributions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cycle"] = get_object_or_404(
            Cycle.objects.select_related("tontine"), uuid=kwargs.get("cycle_uuid")
        )
        context["contributions"] = (
            Contribution.objects.filter(cycle=context["cycle"])
            .select_related("user")
            .order_by("status", "-created_at")
        )

        context["validated_count"] = (
            context["contributions"].filter(status="valide").count()
        )
        context["pending_count"] = (
            context["contributions"]
            .filter(status__in=["en_attente", "en_cours"])
            .count()
        )
        context["rejected_count"] = (
            context["contributions"].filter(status="rejete").count()
        )

        return context


class ContributionStatsView(LoginRequiredMixin, TemplateView):
    template_name = "contributions/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tontine = get_object_or_404(Tontine, uuid=kwargs.get("tontine_uuid"))

        contributions = Contribution.objects.filter(tontine=tontine, status="valide")

        context["tontine"] = tontine
        context["total_amount"] = sum(c.amount for c in contributions)
        context["total_contributions"] = contributions.count()
        context["member_count"] = tontine.member_count

        cycle = tontine.get_current_cycle()
        if cycle:
            context["cycle"] = cycle
            context["cycle_contributions"] = Contribution.objects.filter(
                cycle=cycle, status="valide"
            )
            context["cycle_amount"] = sum(
                c.amount for c in context["cycle_contributions"]
            )
            context["participation_rate"] = (
                (context["cycle_contributions"].count() / tontine.member_count * 100)
                if tontine.member_count > 0
                else 0
            )

        return context
