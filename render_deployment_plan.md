# Comprehensive Django Deployment Plan for Render

This guide provides a complete, step-by-step plan for deploying your Django application to Render's free tier, covering production-ready settings, media file hosting with Cloudinary, Google OAuth, and best practices.

---

### **PART 1 — Verified Django Project Structure**

To support the required features, your project should follow a standard structure. Based on your project, we'll assume the following:

```
/
├── league_app/             # Main Django project folder
│   ├── __init__.py
│   ├── settings.py         # We will replace this
│   ├── urls.py
│   └── wsgi.py
├── content/                # Your Django apps...
├── fantasy/
├── league/
├── users/
├── static/                 # For your global static files (CSS, JS)
├── templates/              # Global templates
├── .gitignore              # To exclude sensitive/unnecessary files
├── manage.py
├── requirements.txt
└── render.yaml             # For Infrastructure-as-Code on Render
```

**Key Configuration Points:**

*   **Static Files:** Your project's static files (like `main.css`) should be in the `static/` directory. `Whitenoise` will be configured to find and serve them.
*   **Media Files:** You have a `media/` folder now, but it will **not** be used in production. User-uploaded files will be handled by **Cloudinary**. You should ensure `media/` is in your `.gitignore`.
*   **Environment Variables:** All secrets (SECRET_KEY, database URLs, API keys) will be managed by Render's environment variable system, not hardcoded in `settings.py`. For local development, you should continue to use an `.env` file (which must be in `.gitignore`).

---

### **PART 2 — Production-Ready `settings.py`**

This is a complete, copy-paste-ready `settings.py` file configured for production on Render. It assumes you have a `users` app with a custom user model.

```python
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
# The 'RENDER' environment variable is set automatically by Render.
DEBUG = 'RENDER' not in os.environ

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
    'cloudinary_storage', # For media files
    'cloudinary',         # For media files
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'widget_tweaks',

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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
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
        # Feel free to alter this value to suit your needs.
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ==============================================================================
# STATIC AND MEDIA FILES (WHITENOISE & CLOUDINARY)
# ==============================================================================

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Use Whitenoise to serve static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cloudinary for Media Files
CLOUDINARY_STORAGE = {
    'CLOUDINARY_URL': os.environ.get('CLOUDINARY_URL')
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
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
```

---

### **PART 3 — `render.yaml` File**

Create a file named `render.yaml` in your project's root directory. This file tells Render how to build and run your services.

```yaml
services:
  # Web Service for Django
  - type: web
    name: league-app
    env: python
    # The region should match your database region
    region: ohio
    plan: free # Or your desired plan
    buildCommand: |
      pip install -r requirements.txt
      python manage.py collectstatic --no-input
    startCommand: "gunicorn league_app.wsgi:application"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: league-app-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true # Let Render generate a random value
      - key: CLOUDINARY_URL
        sync: false # Add this manually in the dashboard
      - key: GOOGLE_CLIENT_ID
        sync: false # Add this manually
      - key: GOOGLE_CLIENT_SECRET
        sync: false # Add this manually

  # PostgreSQL Database
  - type: psql
    name: league-app-db
    region: ohio
    plan: free # Or your desired plan
    # Free tier databases are deleted after 90 days of inactivity.
    # Set 'deletionProtection: true' for paid plans.
```

---

### **PART 4 — Cloudinary Setup Guide**

1.  **Installation:**
    Add the required packages to your `requirements.txt` file and run `pip install -r requirements.txt`:
    ```
    cloudinary
    cloudinary-storage
    dj3-cloudinary-storage
    ```

2.  **`INSTALLED_APPS`:**
    As shown in the `settings.py` above, add `cloudinary` and `cloudinary_storage` to your `INSTALLED_APPS`.

3.  **Get `CLOUDINARY_URL`:**
    *   Sign up for a free Cloudinary account.
    *   On your Cloudinary Dashboard, find the "API Environment variable". It will look like `CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>`.
    *   Copy this entire string.

4.  **Add to Render Dashboard:**
    *   In your Render web service, go to the **Environment** tab.
    *   Click **Add Environment Variable**.
    *   **Key:** `CLOUDINARY_URL`
    *   **Value:** Paste the URL you copied from Cloudinary.

5.  **Example Model Usage:**
    You can use Cloudinary with Django's standard `ImageField`. The `DEFAULT_FILE_STORAGE` setting handles the rest.
    ```python
    # In one of your models.py
    from django.db import models

    class PlayerProfile(models.Model):
        name = models.CharField(max_length=100)
        # This will automatically upload to Cloudinary
        avatar = models.ImageField(upload_to='player_avatars/')
    ```

---

### **PART 5 — Deployment Checklist**

#### **Pre-Deployment:**
1.  [ ] Ensure all required packages (`gunicorn`, `dj-database-url`, `psycopg2-binary`, `whitenoise`, `cloudinary`, `dj3-cloudinary-storage`) are in `requirements.txt`.
2.  [ ] Replace your `settings.py` with the production-ready version from Part 2.
3.  [ ] Create the `render.yaml` file in your project root.
4.  [ ] Add/update your `.gitignore` to exclude `.env`, `db.sqlite3`, and `media/`.
5.  [ ] Run `python manage.py check --deploy` locally to catch common configuration errors.
6.  [ ] Commit all changes to your Git repository.

#### **Post-Deployment on Render:**
1.  [ ] Check the deploy logs in the Render dashboard for any build or runtime errors.
2.  [ ] **Confirm Static Files:** Open your live URL. Right-click, select "Inspect," and go to the "Network" tab. Reload the page. Your CSS and JS files should have a `200` status code.
3.  [ ] **Confirm Cloudinary Upload:**
    *   Go to your app's admin section (you may need to create a superuser via the Render Shell: `python manage.py createsuperuser`).
    *   Try to create or edit a model instance that has an `ImageField`.
    *   Upload an image and save.
    *   Check your Cloudinary Media Library to see if the image appeared there.
4.  [ ] **Test Google OAuth:** Try to log in using the Google login button.

#### **Render Free Tier Pitfalls:**
*   **Slow Initial Load:** Free services "spin down" after 15 minutes of inactivity. The next visit will have a 15-30 second delay while the service starts up. This is normal for the free tier.
*   **Database Deletion:** The free PostgreSQL database will be **deleted** if it's inactive for 90 days.
*   **Build Times:** Builds on the free tier can be slow. Keep your dependencies clean to speed this up.

---

### **PART 6 — Environment Variable Template**

Copy this into the "Secret File" section in your Render service's Environment tab, or add them as individual variables.

```env
# This is a template. Fill in your actual values.

# Django Secret Key (can be auto-generated by Render)
SECRET_KEY=

# From your Cloudinary Dashboard
CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>

# Provided automatically by Render when you link your database
DATABASE_URL=

# From Google Cloud Console for your OAuth App
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```