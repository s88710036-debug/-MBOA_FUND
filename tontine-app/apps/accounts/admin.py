from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, UserConnection, TermsOfService, UserTermsAcceptance


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "status",
        "is_active",
    )
    list_filter = ("role", "status", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Informations supplémentaires",
            {"fields": ("role", "status", "phone", "avatar", "date_joined_tontine")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Informations supplémentaires", {"fields": ("role", "phone")}),
    )

    inlines = (ProfileInline,)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "gender",
        "city",
        "country",
        "terms_accepted",
        "terms_version",
    )
    search_fields = ("user__username", "user__email", "city")
    list_filter = ("gender", "country", "terms_accepted")


@admin.register(UserConnection)
class UserConnectionAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("from_user__username", "to_user__username")


@admin.register(TermsOfService)
class TermsOfServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "content")
    ordering = ("-created_at",)


@admin.register(UserTermsAcceptance)
class UserTermsAcceptanceAdmin(admin.ModelAdmin):
    list_display = ("user", "terms", "accepted_at", "ip_address")
    list_filter = ("accepted_at",)
    search_fields = ("user__username", "user__email")
    ordering = ("-accepted_at",)
