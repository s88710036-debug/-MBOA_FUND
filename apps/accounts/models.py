from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Administrateur"
        TRESORIER = "tresorier", "Trésorier"
        MEMBRE = "membre", "Membre"

    class Status(models.TextChoices):
        ACTIF = "actif", "Actif"
        INACTIF = "inactif", "Inactif"
        SUSPENDU = "suspendu", "Suspendu"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBRE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIF
    )
    phone = PhoneNumberField(blank=True, null=True, verbose_name="Téléphone")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    date_joined_tontine = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_tresorier(self):
        return self.role in [self.Role.TRESORIER, self.Role.SUPER_ADMIN]

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN


class TermsOfService(models.Model):
    title = models.CharField(
        max_length=200, default="Conditions Générales d'Utilisation"
    )
    content = models.TextField()
    version = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Condition d'utilisation"
        verbose_name_plural = "Conditions d'utilisation"

    def __str__(self):
        return f"{self.title} v{self.version}"

    @classmethod
    def get_active_terms(cls):
        return cls.objects.filter(is_active=True).first()


class UserTermsAcceptance(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="terms_acceptances"
    )
    terms = models.ForeignKey(TermsOfService, on_delete=models.CASCADE)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Acceptation des conditions"
        verbose_name_plural = "Acceptations des conditions"
        unique_together = ("user", "terms")

    def __str__(self):
        return f"{self.user.username} - {self.terms.title}"


class Profile(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Homme"
        FEMALE = "F", "Femme"
        OTHER = "O", "Autre"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Sénégal")
    bio = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = PhoneNumberField(blank=True, verbose_name="Téléphone d'urgence")
    terms_accepted = models.BooleanField(default=False, verbose_name="CGU acceptées")
    terms_version = models.CharField(
        max_length=20, blank=True, verbose_name="Version CGU acceptée"
    )

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"

    def __str__(self):
        return f"Profil de {self.user.username}"


class UserConnection(models.Model):
    class ConnectionType(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Accepté"
        REJECTED = "rejected", "Rejeté"

    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="connections_sent"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="connections_received"
    )
    status = models.CharField(
        max_length=20, choices=ConnectionType.choices, default=ConnectionType.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Connexion"
        verbose_name_plural = "Connexions"
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.get_status_display()})"
