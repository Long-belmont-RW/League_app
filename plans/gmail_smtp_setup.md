# Gmail SMTP Setup

## Problem

The application was unable to send emails and was throwing errors related to missing dependencies. When trying to send a test email, the application would crash with `ImportError` or `ModuleNotFoundError`.

## Cause

The main causes of the problem were:

1.  **Incorrect `EMAIL_BACKEND`:** The `EMAIL_BACKEND` in `settings.py` was set to `django.core.mail.backends.console.EmailBackend`, which only prints emails to the console instead of sending them.
2.  **Missing Dependencies:** The following dependencies were not listed in the `requirements.txt` file and were not installed in the virtual environment:
    *   `python-decouple`
    *   `django-widget-tweaks`
    *   `PyJWT`
    *   `cryptography`

## Solution

To resolve the issue, I performed the following steps:

1.  **Updated `EMAIL_BACKEND`:** I changed the `EMAIL_BACKEND` in `league_app/settings.py` to `django.core.mail.backends.smtp.EmailBackend` to enable sending emails through an SMTP server.
2.  **Installed Missing Dependencies:** I installed the missing dependencies into the project's virtual environment using the following commands:
    ```bash
    myvenv\Scripts\python.exe -m pip install python-decouple
    myvenv\Scripts\python.exe -m pip install django-widget-tweaks
    myvenv\Scripts\python.exe -m pip install PyJWT
    myvenv\Scripts\python.exe -m pip install cryptography
    ```
3.  **Updated `requirements.txt`:** I added the newly installed dependencies to the `requirements.txt` file to ensure that they are installed automatically in the future.
4.  **Tested Email Sending:** I sent a test email from the Django shell to verify that the email setup was working correctly.
