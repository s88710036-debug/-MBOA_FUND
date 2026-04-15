from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView, CreateView, ListView, View
from django.contrib import messages
from .models import User
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
)


class LandingPageView(TemplateView):
    template_name = "accounts/landing.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("tontines:dashboard")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Redirect POST requests on '/' to the login page
        return redirect("accounts:login")


class UserLoginView(SuccessMessageMixin, LoginView):
    form_class = UserLoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    success_message = "Connexion réussie ! Bienvenue %(username)s."

    def get_default_redirect_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("tontines:dashboard")


class UserLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("accounts:login")

    def post(self, request):
        logout(request)
        return redirect("accounts:login")


class UserRegistrationView(SuccessMessageMixin, CreateView):
    form_class = UserRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Compte créé avec succès ! Vous pouvez maintenant vous connecter."

    def form_valid(self, form):
        messages.success(self.request, "Inscription réussie ! Veuillez vous connecter.")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = "accounts:login"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context["profile_form"] = ProfileUpdateForm(
                self.request.POST, instance=self.request.user.profile
            )
        else:
            context["profile_form"] = ProfileUpdateForm(
                instance=self.request.user.profile
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context["profile_form"]
        if profile_form.is_valid():
            profile_form.save()
        messages.success(self.request, "Profil mis à jour avec succès !")
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(status="actif").exclude(id=self.request.user.id)
