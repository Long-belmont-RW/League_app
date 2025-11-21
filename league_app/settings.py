# league_app/settings.py

import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# CORE RENDER DEPLOYMENT SETTINGS
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG') == 'TRUE'

ALLOWED_HOSTS = []

# The `RENDER_EXTERNAL_HOSTNAME` environment variable is automatically set by Render.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF configuration for Render
CSRF_TRUSTED_ORIGINS = [f"https://{RENDER_EXTERNAL_HOSTNAME}"] if RENDER_EXTERNAL_HOSTNAME else []


# Application definition
INSTALLED_APPS = [
    # My Apps
    'users.apps.UsersConfig',
    'league.apps.LeagueConfig',
    'content.apps.ContentConfig',
    'fantasy.apps.FantasyConfig',


    # Third Party
   'tailwind',
    'theme',
    'cloudinary_storage', # For media files
    'cloudinary',         # For media files
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'widget_tweaks',
    'debug_toolbar',
    'anymail',

    # Default
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Important for static files
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise middleware
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    
]

INTERNAL_IPS = [
    "127.0.0.1",
]

ROOT_URLCONF = 'league_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'league_app.wsgi.application'

# ==============================================================================
# DATABASE
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# ==============================================================================

DATABASES = {
    'default': dj_database_url.config(
       
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ================================
# STATIC FILES (WHITENOISE)
# ================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'





# ==============================================================================
# GOOGLE OAUTH & ALLAUTH SETTINGS
# ==============================================================================

AUTHENTICATION_BACKENDS = [
   'users.authentication.EmailRoleAuthBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = "users.User"
SITE_ID = 1 # Required by allauth

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = 'account_login'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

# ==============================================================================
# PRODUCTION SECURITY SETTINGS
# ==============================================================================

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Consider setting a more restrictive cookie policy if needed
    # SESSION_COOKIE_SAMESITE = 'Lax'
    # CSRF_COOKIE_SAMESITE = 'Lax'

# Other settings...
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
# EMAIL SETTINGS (BREVO/SMTP)
# ==============================================================================

# Use Anymail's Brevo backend (API) instead of standard SMTP
EMAIL_BACKEND = "anymail.backends.sendinblue.EmailBackend"

ANYMAIL = {
    # Use your existing Brevo API Key (v3)
    # You can find this in Brevo Dashboard -> Settings -> SMTP & API -> Generate new API Key
    "SENDINBLUE_API_KEY": os.environ.get('BREVO_API_KEY'),
}

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'leagueaun@gmail.com')

###all auth fix
SOCIALACCOUNT_LOGIN_ON_GET = True

# Tailwind Configuration
TAILWIND_APP_NAME = 'theme'

# Required for Tailwind to work in development
INTERNAL_IPS = [
    "127.0.0.1",
]

# If we are on Render (production), tell Django where to find npm
if 'RENDER' in os.environ:
    # Render usually installs npm here when NODE_VERSION is set
    NPM_BIN_PATH = '/usr/local/bin/npm' 
else:
    # Local development (Windows)
    NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"




# DEBUGGING STATIC PATHS
print("--- DEBUG: STATIC FILE CONFIG ---")
print(f"BASE_DIR: {BASE_DIR}")
print(f"Looking for static files in: {os.path.join(BASE_DIR, 'static')}")
print(f"Does that folder exist? {os.path.exists(os.path.join(BASE_DIR, 'static'))}")
print("---------------------------------")