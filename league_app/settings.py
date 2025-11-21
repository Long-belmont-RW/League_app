# league_app/settings.py

import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SECURITY & RENDER SETTINGS
# ==============================================================================

SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("DEBUG") == "TRUE"

ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = (
    [f"https://{RENDER_EXTERNAL_HOSTNAME}"] if RENDER_EXTERNAL_HOSTNAME else []
)


# ==============================================================================
# INSTALLED APPS
# ==============================================================================

INSTALLED_APPS = [
    # Apps
    "users.apps.UsersConfig",
    "league.apps.LeagueConfig",
    "content.apps.ContentConfig",
    "fantasy.apps.FantasyConfig",

    # Third-party
    "tailwind",
    "theme",
    "cloudinary_storage",
    "cloudinary",
    "debug_toolbar",
    "widget_tweaks",
    "anymail",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]


ROOT_URLCONF = "league_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "league_app.wsgi.application"


# ==============================================================================
# DATABASE
# ==============================================================================

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ==============================================================================
# STATIC & MEDIA (PRODUCTION READY)
# ==============================================================================

# ---------------------------- STATIC FILES -------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ⚠️ REQUIRED FOR CLOUDINARY STORAGE COMPATIBILITY
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Django 5.2-compliant storage API
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Prevent build failures if a referenced file is missing
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = "/media/"

CLOUDINARY_STORAGE = {
    "CLOUDINARY_URL": os.environ.get("CLOUDINARY_URL")
}


# ==============================================================================
# AUTHENTICATION & ALLAUTH
# ==============================================================================

AUTH_USER_MODEL = "users.User"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "users.authentication.EmailRoleAuthBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
LOGIN_URL = "account_login"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

SOCIALACCOUNT_LOGIN_ON_GET = True


# ==============================================================================
# TAILWIND CONFIGURATION
# ==============================================================================

TAILWIND_APP_NAME = "theme"

# NPM path for Render or Windows dev
NPM_BIN_PATH = os.environ.get("NPM_BIN_PATH")
if not NPM_BIN_PATH:
    if "RENDER" in os.environ:
        NPM_BIN_PATH = "/usr/local/bin/npm"
    else:
        NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"


# ==============================================================================
# EMAIL (BREVO — ANYMAIL)
# ==============================================================================

EMAIL_BACKEND = "anymail.backends.sendinblue.EmailBackend"

ANYMAIL = {
    "SENDINBLUE_API_KEY": os.environ.get("BREVO_API_KEY"),
}

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "leagueaun@gmail.com")


# ==============================================================================
# PRODUCTION SECURITY
# ==============================================================================

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ==============================================================================
# DJANGO BASICS
# ==============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
