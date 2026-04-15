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

app_name = "accounts"

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileUpdateView.as_view(), name="profile_edit"),
    path("users/", UserListView.as_view(), name="user_list"),
]
