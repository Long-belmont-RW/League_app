# Django-Allauth Social Login Migration Plan

This guide provides a complete walkthrough for integrating `django-allauth` for social logins (Google, GitHub) into your existing Django project, while preserving your custom email-based authentication system.

---

### Step 1: Install Required Packages

First, install `django-allauth` using pip:

```bash
(myvenv) pip install django-allauth
```

### Step 2: Apply Migrations

Run the Django migrations to create the necessary database tables for `allauth`:

```bash
(myvenv) python manage.py migrate
```

### Step 3: Configure OAuth Credentials

You need to get an OAuth **Client ID** and **Secret Key** from each social provider you want to support.

#### For Google:

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project or select an existing one.
3.  Navigate to **APIs & Services > Credentials**.
4.  Click **Create Credentials > OAuth client ID**.
5.  Select **Web application** as the application type.
6.  Under **Authorized JavaScript origins**, add your domain (e.g., `http://127.0.0.1:8000`).
7.  Under **Authorized redirect URIs**, add the `allauth` callback URL. It follows the pattern `http://<your-domain>/accounts/<provider>/login/callback/`.
    *   For local development, add: `http://127.0.0.1:8000/accounts/google/login/callback/`
8.  Click **Create**. Copy the **Client ID** and **Client Secret**.

### Step 4: Add Social Applications in Django Admin

1.  Start your development server:
    ```bash
    (myvenv) python manage.py runserver
    ```
2.  Log in to the Django admin panel (e.g., `http://127.0.0.1:8000/admin/`).
3.  Navigate to **Social Accounts > Social applications** and click **Add social application**.
4.  Create an entry for Google:
    *   **Provider:** Google
    *   **Name:** Google Auth
    *   **Client ID:** Paste the ID from the Google Cloud Console.
    *   **Secret key:** Paste the secret from the Google Cloud Console.
    *   **Sites:** Move your site (`example.com` or `127.0.0.1:8000`) to the **Chosen sites** box.
5.  Save the application. Repeat this process for any other providers like GitHub.

### Step 5: Update Your Login Template

In your `login.html` template, add the following snippet to display the social login buttons. This should be placed within your login form or wherever you want the buttons to appear.

```html
{% comment %} Add this to the top of your login.html template {% endcomment %}
{% load socialaccount %}

{% comment %} Add this where you want the Google button to appear {% endcomment %}
<div class="my-4">
    <p class="text-center">Or sign in with:</p>
    <a href="{% provider_login_url 'google' %}" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full w-full text-center block">
        Sign in with Google
    </a>
    
    {% comment %} Optional: Add a GitHub button {% endcomment %}
    <a href="{% provider_login_url 'github' %}" class="bg-gray-800 hover:bg-gray-900 text-white font-bold py-2 px-4 rounded-full w-full text-center block mt-2">
        Sign in with GitHub
    </a>
</div>
```

### Step 6: Create the Profile Completion Page

Your `users.User` model requires `birth` and `gender`. The adapter I created will redirect users with incomplete profiles to `/complete-profile/`. You need to create the view, URL, and template for this page.

1.  **URL (`users/urls.py`):**
    ```python
    path('complete-profile/', views.complete_profile_view, name='complete_profile'),
    ```
2.  **View (`users/views.py`):** Create a view that handles a form to update the user's `birth` and `gender`.
3.  **Template:** Create a template with a form for the missing fields.

### Step 7: Testing Strategy

Thoroughly test the implementation to ensure it works as expected for all scenarios.

#### Test Case 1: New User via Social Login

1.  Log out of your application.
2.  Go to your login page.
3.  Click the "Sign in with Google" button.
4.  Authenticate with a Google account that has **never** been used in your app before.
5.  **Expected Outcome:**
    *   A new `User` account is created in your database with the email from Google.
    *   The user's `first_name` and `last_name` are populated from their Google profile.
    *   The user is immediately redirected to the `/complete-profile/` page because `birth` and `gender` are missing.

#### Test Case 2: Existing User via Social Login

1.  Create a user in your app using your standard email/password registration form. Use an email address that matches a Google account you can test with.
2.  Log out.
3.  Go to the login page and click "Sign in with Google".
4.  Authenticate with the Google account corresponding to the user you just created.
5.  **Expected Outcome:**
    *   No new user is created.
    *   The Google social account is linked to the existing user account.
    *   The user is logged in and redirected to the `LOGIN_REDIRECT_URL` (or `/complete-profile/` if their profile was incomplete).

#### Test Case 3: Preserve Custom Authentication

1.  Go to your registration page and create a new user with an email and password.
2.  Log out and log back in using the email and password you just registered.
3.  **Expected Outcome:**
    *   The custom registration and login flows should continue to work without any interference from `django-allauth`.

---

This completes the integration. Your application is now configured to handle social logins gracefully alongside your existing authentication system.
