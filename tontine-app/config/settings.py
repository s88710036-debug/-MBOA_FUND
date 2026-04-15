from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-key-change-in-production-!@#$%^&*()"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com"
).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_htmx",
    "crispy_forms",
    "crispy_bootstrap5",
    "phonenumber_field",
    "apps.accounts",
    "apps.tontines",
    "apps.contributions",
    "apps.draws",
    "apps.notifications",
    "apps.reports",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.accounts.middleware.LastSeenMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.notifications.context_processors.notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

import dj_database_url

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.parse(
        os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "tontines:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

LANGUAGE_CODE = "fr-FR"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "TontineApp <noreply@tontine.app"

PAGINATION_PAGE_SIZE = 20

MOBILE_MONEY = {
    "ORANGE_MONEY": {
        "API_KEY": os.environ.get("ORANGE_MONEY_API_KEY", ""),
        "MERCHANT_ID": os.environ.get("ORANGE_MONEY_MERCHANT_ID", ""),
        "SANDBOX": DEBUG,
    },
    "WAVE": {
        "API_KEY": os.environ.get("WAVE_API_KEY", ""),
        "SANDBOX": DEBUG,
    },
}

NOTIFICATION_SETTINGS = {
    "EMAIL_ENABLED": False,
    "PUSH_ENABLED": False,
    "IN_APP_ENABLED": True,
}

# ============================================================
# CONFIGURATION DES PAIEMENTS
# ============================================================

MOBILE_MONEY = {
    "ORANGE_MONEY": {
        "API_KEY": os.environ.get("ORANGE_MONEY_API_KEY", ""),
        "MERCHANT_ID": os.environ.get("ORANGE_MONEY_MERCHANT_ID", ""),
        "CALLBACK_URL": os.environ.get(
            "ORANGE_MONEY_CALLBACK_URL",
            "http://localhost:8000/payments/webhooks/orange/",
        ),
        "SANDBOX_URL": "https://api-sandbox.orange.com/orange-money-webpay",
        "PRODUCTION_URL": "https://api.orange.com/orange-money-webpay",
    },
    "WAVE": {
        "API_KEY": os.environ.get("WAVE_API_KEY", ""),
        "API_SECRET": os.environ.get("WAVE_API_SECRET", ""),
        "CALLBACK_URL": os.environ.get(
            "WAVE_CALLBACK_URL", "http://localhost:8000/payments/webhooks/wave/"
        ),
        "SANDBOX_URL": "https://api.wave.com/v1/checkout",
        "PRODUCTION_URL": "https://api.wave.com/v1/checkout",
    },
}

STRIPE_SETTINGS = {
    "PUBLIC_KEY": os.environ.get("STRIPE_PUBLIC_KEY", ""),
    "SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY", ""),
    "WEBHOOK_SECRET": os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
    "CALLBACK_URL": "http://localhost:8000/payments/webhooks/stripe/",
    "SANDBOX": DEBUG,
}

SMS_SETTINGS = {
    "DEFAULT_PROVIDER": "africas_talking",
    "AFRICAS_TALKING": {
        "API_KEY": os.environ.get("AFRICAS_TALKING_API_KEY", ""),
        "USERNAME": os.environ.get("AFRICAS_TALKING_USERNAME", "sandbox"),
    },
    "RETRY_ON_FAILURE": True,
    "MAX_SMS_RETRIES": 3,
}

PAYMENT_SETTINGS = {
    "MAX_RETRIES": 3,
    "RETRY_INTERVAL": 3600,
    "SANDBOX_SIMULATION": DEBUG,
}
