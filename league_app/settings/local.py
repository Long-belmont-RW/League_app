from .base import *

# Local Development Settings
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]


# Print emails to console instead of sending them
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Remove whitenoise.runserver_nostatic to allow runserver to serve static files from STATICFILES_DIRS
if "whitenoise.runserver_nostatic" in INSTALLED_APPS:
    INSTALLED_APPS.remove("whitenoise.runserver_nostatic")

INTERNAL_IPS = ["127.0.0.1"]

# Database - Use SQLite locally by default if DATABASE_URL is not set
import os
if not os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Security - Disable SSL redirect for local dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
