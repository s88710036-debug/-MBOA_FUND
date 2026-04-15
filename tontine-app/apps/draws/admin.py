from django.contrib import admin
from .models import Draw, DrawParticipant, DrawWinner, DrawHistory


class DrawParticipantInline(admin.TabularInline):
    model = DrawParticipant
    extra = 0


class DrawWinnerInline(admin.TabularInline):
    model = DrawWinner
    extra = 0
    readonly_fields = ("uuid", "winner", "prize_amount", "position", "status")


class DrawAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tontine",
        "cycle",
        "status",
        "selection_method",
        "draw_date",
        "prize_amount",
    )
    list_filter = ("status", "selection_method", "tontine", "draw_date")
    search_fields = ("name", "tontine__name")
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = [DrawParticipantInline, DrawWinnerInline]


class DrawWinnerAdmin(admin.ModelAdmin):
    list_display = ("winner", "draw", "prize_amount", "position", "status", "paid_at")
    list_filter = ("status", "draw__tontine")
    search_fields = ("winner__username", "payout_reference")


class DrawHistoryAdmin(admin.ModelAdmin):
    list_display = ("draw", "action", "performed_by", "created_at")
    list_filter = ("action", "created_at")


admin.site.register(Draw, DrawAdmin)
admin.site.register(DrawParticipant)
admin.site.register(DrawWinner, DrawWinnerAdmin)
admin.site.register(DrawHistory, DrawHistoryAdmin)
