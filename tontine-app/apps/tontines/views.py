from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from django.views.generic.edit import FormView
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from .models import Tontine, TontineMembership, Cycle
from .forms import TontineForm, JoinTontineForm, CycleForm, MembershipActionForm


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "tontines/dashboard.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["my_tontines"] = Tontine.objects.filter(
            memberships__user=user, memberships__status="actif"
        ).distinct()

        context["pending_memberships"] = TontineMembership.objects.filter(
            user=user, status="en_attente"
        ).select_related("tontine")

        context["treasurer_tontines"] = Tontine.objects.filter(
            memberships__user=user, memberships__role="tresorier", status="active"
        ).distinct()

        context["public_tontines"] = Tontine.objects.filter(
            is_public=True, status__in=["en_creation", "active"]
        ).exclude(memberships__user=user)[:5]

        return context


class TontineListView(LoginRequiredMixin, ListView):
    model = Tontine
    template_name = "tontines/tontine_list.html"
    context_object_name = "tontines"
    paginate_by = 12

    def get_queryset(self):
        queryset = Tontine.objects.filter(
            memberships__user=self.request.user, memberships__status="actif"
        ).distinct()

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")


class TontineCreateView(LoginRequiredMixin, CreateView):
    model = Tontine
    form_class = TontineForm
    template_name = "tontines/tontine_form.html"
    success_url = reverse_lazy("tontines:list")

    def form_valid(self, form):
        form.instance.creator = self.request.user
        response = super().form_valid(form)

        TontineMembership.objects.create(
            tontine=self.object,
            user=self.request.user,
            role="tresorier",
            status="actif",
        )

        messages.success(
            self.request, f'Tontine "{self.object.name}" créée avec succès !'
        )
        return response


class TontineDetailView(LoginRequiredMixin, DetailView):
    model = Tontine
    template_name = "tontines/tontine_detail.html"
    context_object_name = "tontine"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return Tontine.objects.all().prefetch_related("memberships", "cycles")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            membership = self.object.memberships.get(user=user)
            context["user_membership"] = membership
            context["is_tresorier"] = membership.role == "tresorier"
        except TontineMembership.DoesNotExist:
            context["user_membership"] = None
            context["is_tresorier"] = False

        context["active_cycle"] = self.object.get_current_cycle()
        context["active_members"] = self.object.memberships.filter(status="actif")
        context["pending_members"] = self.object.memberships.filter(status="en_attente")

        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        try:
            membership = self.object.memberships.get(user=request.user)
            if membership.status != "actif":
                messages.warning(request, "Votre demande est en attente de validation.")
        except TontineMembership.DoesNotExist:
            pass

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class TontineUpdateView(LoginRequiredMixin, UpdateView):
    model = Tontine
    form_class = TontineForm
    template_name = "tontines/tontine_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return Tontine.objects.filter(
            memberships__user=self.request.user, memberships__role="tresorier"
        )

    def form_valid(self, form):
        messages.success(self.request, "Tontine mise à jour avec succès !")
        return super().form_valid(form)


class TontineDeleteView(LoginRequiredMixin, DeleteView):
    model = Tontine
    template_name = "tontines/tontine_confirm_delete.html"
    success_url = reverse_lazy("tontines:list")
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return Tontine.objects.filter(creator=self.request.user)


class JoinTontineView(LoginRequiredMixin, FormView):
    form_class = JoinTontineForm
    template_name = "tontines/join_tontine.html"
    success_url = reverse_lazy("tontines:list")

    def form_valid(self, form):
        code = form.cleaned_data["invite_code"]
        tontine = get_object_or_404(Tontine, invite_code=code)

        membership, created = TontineMembership.objects.get_or_create(
            tontine=tontine,
            user=self.request.user,
            defaults={"role": "membre", "status": "en_attente"},
        )

        if not created:
            if membership.status == "en_attente":
                messages.info(self.request, "Votre demande est déjà en attente.")
            elif membership.status == "actif":
                messages.info(self.request, "Vous êtes déjà membre de cette tontine.")
        else:
            messages.success(
                self.request, f'Demande envoyée pour rejoindre "{tontine.name}" !'
            )

        return redirect("tontines:detail", uuid=tontine.uuid)


class JoinByCodeView(LoginRequiredMixin, FormView):
    """Page pour rejoindre une tontine via un code d'invitation (sans uuid pré-connu)."""

    form_class = JoinTontineForm
    template_name = "tontines/join_tontine.html"
    success_url = reverse_lazy("tontines:list")

    def form_valid(self, form):
        code = form.cleaned_data["invite_code"]
        tontine = get_object_or_404(Tontine, invite_code=code)

        membership, created = TontineMembership.objects.get_or_create(
            tontine=tontine,
            user=self.request.user,
            defaults={"role": "membre", "status": "en_attente"},
        )

        if not created:
            if membership.status == "en_attente":
                messages.info(self.request, "Votre demande est déjà en attente.")
            elif membership.status == "actif":
                messages.info(self.request, "Vous êtes déjà membre de cette tontine.")
        else:
            messages.success(
                self.request, f'Demande envoyée pour rejoindre "{tontine.name}" !'
            )

        return redirect("tontines:detail", uuid=tontine.uuid)


class LeaveTontineView(LoginRequiredMixin, View):
    def post(self, request, uuid):
        tontine = get_object_or_404(Tontine, uuid=uuid)

        try:
            membership = TontineMembership.objects.get(
                tontine=tontine, user=request.user
            )

            if membership.role == "tresorier":
                other_tresoriers = (
                    TontineMembership.objects.filter(
                        tontine=tontine, role="tresorier", status="actif"
                    )
                    .exclude(user=request.user)
                    .count()
                )

                if other_tresoriers == 0:
                    messages.error(
                        request,
                        "Vous êtes le seul trésorier. Désignez un autre avant de quitter.",
                    )
                    return redirect("tontines:detail", uuid=uuid)

            membership.status = "quitte"
            membership.save()
            messages.success(request, f'Vous avez quitté "{tontine.name}".')
        except TontineMembership.DoesNotExist:
            messages.error(request, "Vous n'êtes pas membre de cette tontine.")

        return redirect("tontines:list")


class ManageMembersView(LoginRequiredMixin, TemplateView):
    template_name = "tontines/manage_members.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return Tontine.objects.filter(
            memberships__user=self.request.user, memberships__role="tresorier"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tontine"] = get_object_or_404(
            self.get_queryset(), uuid=kwargs.get("uuid")
        )
        context["pending_members"] = TontineMembership.objects.filter(
            tontine=context["tontine"], status="en_attente"
        ).select_related("user")
        context["active_members"] = TontineMembership.objects.filter(
            tontine=context["tontine"], status="actif"
        ).select_related("user")
        return context


class MembershipActionView(LoginRequiredMixin, View):
    def post(self, request, uuid):
        tontine = get_object_or_404(Tontine, uuid=uuid)

        try:
            tresorier_membership = TontineMembership.objects.get(
                tontine=tontine, user=request.user, role="tresorier", status="actif"
            )
        except TontineMembership.DoesNotExist:
            return HttpResponseForbidden("Vous n'êtes pas autorisé.")

        membership_id = request.POST.get("membership_id")
        action = request.POST.get("action")

        try:
            membership = TontineMembership.objects.get(
                id=membership_id, tontine=tontine
            )
        except TontineMembership.DoesNotExist:
            messages.error(request, "Membre non trouvé.")
            return redirect("tontines:manage_members", uuid=uuid)

        if action == "approve":
            membership.status = "actif"
            membership.approved_by = request.user
            membership.approved_at = timezone.now()
            messages.success(request, f"{membership.user} a été approuvé.")
        elif action == "suspend":
            membership.status = "suspendu"
            messages.warning(request, f"{membership.user} a été suspendu.")
        elif action == "reactivate":
            membership.status = "actif"
            messages.success(request, f"{membership.user} a été réactivé.")
        elif action == "remove":
            membership.status = "quitte"
            messages.info(request, f"{membership.user} a été retiré.")
        else:
            messages.error(request, "Action non reconnue.")
            return redirect("tontines:manage_members", uuid=uuid)

        membership.save()
        return redirect("tontines:manage_members", uuid=uuid)


class CycleCreateView(LoginRequiredMixin, CreateView):
    model = Cycle
    form_class = CycleForm
    template_name = "tontines/cycle_form.html"

    def get_queryset(self):
        return Tontine.objects.filter(
            memberships__user=self.request.user, memberships__role="tresorier"
        )

    def get(self, request, *args, **kwargs):
        self.tontine = get_object_or_404(self.get_queryset(), uuid=kwargs.get("uuid"))
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tontine"] = self.tontine
        return kwargs

    def form_valid(self, form):
        form.instance.tontine = self.tontine
        form.instance.number = self.tontine.cycles.count() + 1
        form.instance.total_expected = (
            form.cleaned_data["amount_per_member"] * self.tontine.member_count
        )
        response = super().form_valid(form)

        self.tontine.cycles.update(is_active=False)
        form.instance.is_active = True
        form.instance.save()

        messages.success(self.request, f'Cycle "{form.instance.name}" créé et activé !')
        return response

    def get_success_url(self):
        return reverse("tontines:detail", kwargs={"uuid": self.tontine.uuid})


class ActivateTontineView(LoginRequiredMixin, View):
    def post(self, request, uuid):
        tontine = get_object_or_404(Tontine, uuid=uuid)

        try:
            TontineMembership.objects.get(
                tontine=tontine, user=request.user, role="tresorier", status="actif"
            )
        except TontineMembership.DoesNotExist:
            return HttpResponseForbidden("Vous n'êtes pas autorisé.")

        if not tontine.can_start:
            messages.error(request, "Impossible de démarrer. Membres insuffisants.")
            return redirect("tontines:detail", uuid=uuid)

        tontine.status = "active"
        tontine.start_date = timezone.now().date()
        tontine.save()

        if not tontine.cycles.exists():
            Cycle.objects.create(
                tontine=tontine,
                number=1,
                name=f"Tour 1",
                start_date=timezone.now().date(),
                amount_per_member=tontine.amount_per_member,
                total_expected=tontine.amount_per_member * tontine.member_count,
                is_active=True,
            )

        messages.success(request, f'Tontine "{tontine.name}" est maintenant active !')
        return redirect("tontines:detail", uuid=uuid)
