from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, View
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from apps.tontines.models import Tontine, TontineMembership, Cycle
from apps.contributions.models import Contribution
from apps.draws.models import Draw, DrawWinner
from .models import Report, MonthlyReport


class ReportDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/report_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tontine_uuid = self.kwargs.get("tontine_uuid")
        if tontine_uuid:
            tontine = get_object_or_404(Tontine, uuid=tontine_uuid)
        else:
            tontine = Tontine.objects.filter(
                memberships__user=self.request.user, memberships__status="actif"
            ).first()

        if not tontine:
            return context

        context["tontine"] = tontine

        contributions = Contribution.objects.filter(tontine=tontine, status="valide")
        context["total_contributions"] = (
            contributions.aggregate(total=Sum("amount"))["total"] or 0
        )
        context["contribution_count"] = contributions.count()

        context["member_count"] = tontine.memberships.filter(status="actif").count()

        winners = DrawWinner.objects.filter(draw__tontine=tontine)
        context["total_winnings"] = (
            winners.aggregate(total=Sum("prize_amount"))["total"] or 0
        )
        context["winner_count"] = winners.count()

        context["cycles"] = Cycle.objects.filter(tontine=tontine).order_by("-number")[
            :6
        ]
        context["recent_contributions"] = (
            Contribution.objects.filter(tontine=tontine)
            .select_related("user", "cycle")
            .order_by("-created_at")[:10]
        )

        return context


class ContributionReportView(LoginRequiredMixin, ListView):
    model = Contribution
    template_name = "reports/contribution_report.html"
    context_object_name = "contributions"

    def get_queryset(self):
        tontine_uuid = self.kwargs.get("tontine_uuid")
        queryset = Contribution.objects.filter(tontine__uuid=tontine_uuid)

        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        date_from = self.request.GET.get("from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.GET.get("to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.select_related("user", "cycle", "tontine").order_by(
            "-created_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tontine"] = get_object_or_404(
            Tontine, uuid=self.kwargs.get("tontine_uuid")
        )
        context["total_amount"] = sum(
            c.amount for c in context["contributions"] if c.status == "valide"
        )
        context["validated_count"] = len(
            [c for c in context["contributions"] if c.status == "valide"]
        )
        context["pending_count"] = len(
            [
                c
                for c in context["contributions"]
                if c.status in ["en_attente", "en_cours"]
            ]
        )
        return context


class MemberReportView(LoginRequiredMixin, TemplateView):
    template_name = "reports/member_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tontine = get_object_or_404(Tontine, uuid=kwargs.get("tontine_uuid"))
        context["tontine"] = tontine

        members = TontineMembership.objects.filter(tontine=tontine).select_related(
            "user"
        )

        member_stats = []
        for m in members:
            contributions = Contribution.objects.filter(user=m.user, tontine=tontine)
            validated = contributions.filter(status="valide")
            member_stats.append(
                {
                    "membership": m,
                    "total_contributions": validated.aggregate(total=Sum("amount"))[
                        "total"
                    ]
                    or 0,
                    "contribution_count": validated.count(),
                    "winnings": DrawWinner.objects.filter(
                        winner=m.user, draw__tontine=tontine
                    ).count(),
                }
            )

        context["member_stats"] = sorted(
            member_stats, key=lambda x: x["total_contributions"], reverse=True
        )
        return context


class FinancialReportView(LoginRequiredMixin, TemplateView):
    template_name = "reports/financial_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tontine = get_object_or_404(Tontine, uuid=kwargs.get("tontine_uuid"))
        context["tontine"] = tontine

        contributions = Contribution.objects.filter(tontine=tontine, status="valide")
        context["total_collected"] = (
            contributions.aggregate(total=Sum("amount"))["total"] or 0
        )
        context["expected_amount"] = tontine.amount_per_member * tontine.member_count

        winners = DrawWinner.objects.filter(draw__tontine=tontine)
        context["total_distributed"] = (
            winners.aggregate(total=Sum("prize_amount"))["total"] or 0
        )
        context["balance"] = context["total_collected"] - context["total_distributed"]

        context["contributions_by_method"] = (
            contributions.values("payment_method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        return context


class ExportReportView(LoginRequiredMixin, View):
    def get(self, request, tontine_uuid, report_type):
        tontine = get_object_or_404(Tontine, uuid=tontine_uuid)

        if report_type == "contributions":
            contributions = Contribution.objects.filter(tontine=tontine).select_related(
                "user", "cycle"
            )

            csv_content = "Membre,Cycle,Montant,Méthode,Statut,Date\n"
            for c in contributions:
                csv_content += f"{c.user.get_full_name()},{c.cycle.name},{c.amount},{c.payment_method},{c.status},{c.created_at.strftime('%Y-%m-%d')}\n"

            response = HttpResponse(csv_content, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="contributions_{tontine.name}_{timezone.now().strftime("%Y%m%d")}.csv"'
            )
            return response

        return HttpResponse("Format non supporté", status=400)
