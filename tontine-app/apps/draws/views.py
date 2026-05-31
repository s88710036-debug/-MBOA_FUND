from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, View
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from apps.tontines.models import Tontine, TontineMembership, Cycle
from apps.contributions.models import Contribution
from apps.notifications.models import Notification
from .models import Draw, DrawWinner, DrawHistory
from .forms import DrawForm, DrawWinnerForm


class DrawListView(LoginRequiredMixin, ListView):
    model = Draw
    template_name = "draws/draw_list.html"
    context_object_name = "draws"
    paginate_by = 20

    def get_queryset(self):
        return (
            Draw.objects.filter(
                tontine__memberships__user=self.request.user,
                tontine__memberships__status="actif",
            )
            .distinct()
            .select_related("tontine", "cycle")
        )


class DrawDetailView(LoginRequiredMixin, TemplateView):
    template_name = "draws/draw_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        draw = get_object_or_404(
            Draw.objects.select_related("tontine", "cycle", "created_by"),
            uuid=kwargs.get("uuid"),
        )
        context["draw"] = draw
        context["winners"] = draw.winners.select_related("winner")
        context["eligible_count"] = len(draw.get_eligible_participants())
        return context


class DrawCreateView(LoginRequiredMixin, CreateView):
    model = Draw
    form_class = DrawForm
    template_name = "draws/draw_form.html"

    def get_cycle(self):
        return get_object_or_404(
            Cycle.objects.select_related("tontine"), uuid=self.kwargs.get("cycle_uuid")
        )

    def get(self, request, *args, **kwargs):
        cycle = self.get_cycle()

        try:
            TontineMembership.objects.get(
                tontine=cycle.tontine,
                user=request.user,
                role="tresorier",
                status="actif",
            )
        except TontineMembership.DoesNotExist:
            messages.error(request, "Seul un trésorier peut créer un tirage.")
            return redirect("tontines:detail", uuid=cycle.tontine.uuid)

        if not cycle.contributions.filter(status="valide").exists():
            messages.warning(
                request, "Aucune cotisation validée. Le tirage ne peut pas avoir lieu."
            )

        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cycle"] = self.get_cycle()
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["created_by"] = self.request.user
        return initial

    def form_valid(self, form):
        cycle = self.get_cycle()
        form.instance.cycle = cycle
        form.instance.tontine = cycle.tontine
        form.instance.number = cycle.draws.count() + 1
        form.instance.total_pot = cycle.total_amount
        form.instance.prize_amount = cycle.total_amount
        form.instance.created_by = self.request.user

        response = super().form_valid(form)

        DrawHistory.objects.create(
            draw=self.object,
            action="creation",
            description=f"Tirage créé par {self.request.user}",
            performed_by=self.request.user,
        )

        messages.success(
            self.request, f'Tirage "{form.instance.name}" créé avec succès !'
        )
        return response

    def get_success_url(self):
        return reverse("draws:detail", kwargs={"uuid": self.object.uuid})


class PerformDrawView(LoginRequiredMixin, View):
    def get(self, request, uuid):
        draw = get_object_or_404(Draw, uuid=uuid)

        try:
            TontineMembership.objects.get(
                tontine=draw.tontine,
                user=request.user,
                role="tresorier",
                status="actif",
            )
        except TontineMembership.DoesNotExist:
            return HttpResponseForbidden("Vous n'êtes pas autorisé.")

        if draw.status != "planifie":
            messages.error(request, "Ce tirage ne peut pas être effectué.")
            return redirect("draws:detail", uuid=uuid)

        eligible = draw.get_eligible_participants()
        if len(eligible) < draw.winner_count:
            messages.error(
                request, f"Pas assez de participants éligibles ({len(eligible)})."
            )
            return redirect("draws:detail", uuid=uuid)

        winners = draw.perform_draw()

        DrawHistory.objects.create(
            draw=draw,
            action="tirage_effectue",
            description=f"Tirage effectué. Gagnants: {', '.join(w.username for w in [DrawWinner.objects.get(draw=draw, position=i + 1).winner for i in range(len(winners))])}",
            performed_by=request.user,
        )

        for winner in winners:
            Notification.objects.create(
                user=winner.winner,
                title="Félicitations ! Vous avez gagné !",
                message=f'Vous avez gagné {winner.prize_amount} XAF au tirage "{draw.name}" de {draw.tontine.name} !',
                notification_type="success",
            )

        for member in draw.tontine.memberships.filter(status="actif").exclude(
            user__in=[w.winner for w in winners]
        ):
            Notification.objects.create(
                user=member.user,
                title="Tirage effectué",
                message=f'Le tirage "{draw.name}" a été effectué. Le gagnant est {winners[0].winner.get_full_name()}.',
                notification_type="info",
            )

        messages.success(
            request, f"Tirage effectué ! {len(winners)} gagnant(s) sélectionné(s)."
        )
        return redirect("draws:detail", uuid=uuid)


class UpdateWinnerStatusView(LoginRequiredMixin, UpdateView):
    model = DrawWinner
    form_class = DrawWinnerForm
    template_name = "draws/winner_status_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return DrawWinner.objects.filter(
            draw__tontine__memberships__user=self.request.user,
            draw__tontine__memberships__role="tresorier",
            draw__tontine__memberships__status="actif",
        ).distinct()

    def form_valid(self, form):
        winner = form.instance

        if form.cleaned_data["status"] == "recu" and not winner.confirmed_at:
            winner.confirmed_at = timezone.now()
            winner.paid_at = timezone.now()

        response = super().form_valid(form)

        Notification.objects.create(
            user=winner.winner,
            title="Mise à jour du paiement",
            message=f"Le statut de votre gain a été mis à jour: {winner.get_status_display()}",
            notification_type="info",
        )

        messages.success(self.request, "Statut du gagnant mis à jour.")
        return response

    def get_success_url(self):
        return reverse("draws:detail", kwargs={"uuid": self.object.draw.uuid})


class CycleDrawsView(LoginRequiredMixin, TemplateView):
    template_name = "draws/cycle_draws.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cycle = get_object_or_404(
            Cycle.objects.select_related("tontine"), uuid=kwargs.get("cycle_uuid")
        )
        context["cycle"] = cycle
        context["draws"] = Draw.objects.filter(cycle=cycle).select_related("created_by")
        context["total_prize"] = sum(d.prize_amount for d in context["draws"])
        return context
