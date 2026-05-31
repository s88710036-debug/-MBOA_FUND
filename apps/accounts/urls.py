from django.urls import path
from .views import (
    LandingPageView,
    UserLoginView,
    UserLogoutView,
    UserRegistrationView,
    ProfileView,
    ProfileUpdateView,
    UserListView,
)
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from .views import check_username

app_name = "accounts"

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileUpdateView.as_view(), name="profile_edit"),
    path("users/", UserListView.as_view(), name="user_list"),
    # Password reset (forgot password)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
        # HTMX helpers
        path("htmx/check-username/", check_username, name="htmx_check_username"),
]
