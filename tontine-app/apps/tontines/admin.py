from django.contrib import admin
from .models import Tontine, TontineMembership, Cycle


class MembershipInline(admin.TabularInline):
    model = TontineMembership
    extra = 0
    readonly_fields = ("joined_at",)


class CycleInline(admin.TabularInline):
    model = Cycle
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Tontine)
class TontineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "creator",
        "status",
        "frequency",
        "amount_per_member",
        "member_count",
        "is_public",
        "created_at",
    )
    list_filter = ("status", "frequency", "is_public", "created_at")
    search_fields = ("name", "creator__username", "invite_code")
    readonly_fields = ("uuid", "invite_code", "created_at", "updated_at")
    inlines = [MembershipInline, CycleInline]


@admin.register(TontineMembership)
class TontineMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "tontine", "role", "status", "joined_at")
    list_filter = ("role", "status", "tontine")
    search_fields = ("user__username", "tontine__name")


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tontine",
        "number",
        "status",
        "is_active",
        "start_date",
        "total_amount",
    )
    list_filter = ("status", "is_active", "tontine")
    search_fields = ("name", "tontine__name")
