from config.settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

DEBUG = False

SMS_SETTINGS = {
    "DEFAULT_PROVIDER": "africas_talking",
    "AFRICAS_TALKING": {
        "API_KEY": "",
        "USERNAME": "sandbox",
    },
    "RETRY_ON_FAILURE": False,
    "MAX_SMS_RETRIES": 0,
}
