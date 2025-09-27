from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import messages
from allauth.account.views import login as account_login

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin):
        """
        Allow social signups. Together with SOCIALACCOUNT_AUTO_SIGNUP=True,
        users coming from Google can be created without prompting for password.
        The pre_social_login hook below will link to existing users by verified email.
        """
        return True

    def pre_social_login(self, request: HttpRequest, sociallogin):
        """
        Link a social account to an existing user if the provider's email matches
        an existing user email (case-insensitive) and is verified.

        If the email is unverified and clashes with an existing user, block
        auto-signup and redirect the user to the normal login flow with a message.
        """
        # If this social account is already linked to a user, nothing to do.
        if sociallogin.is_existing:
            return

        # Extract email and verification status from provider data
        data = sociallogin.account.extra_data or {}
        email = data.get("email") or sociallogin.user.email
        email_verified = data.get("email_verified") or data.get("verified_email")

        if not email:
            # No email provided by the provider; let allauth handle prompts if any
            return

        try:
            # Case-insensitive match to existing user
            user = User._default_manager.get(email__iexact=email)
        except User.DoesNotExist:
            # No existing user; allow normal (auto) signup flow to proceed
            return

        if email_verified:
            # Associate this social login with the existing user
            sociallogin.user = user
            sociallogin.account.user = user
            # allauth will handle creating/attaching the SocialAccount and logging in
            return

        # Email not verified and would clash with an existing account -> block
        messages.error(
            request,
            "Please verify your Google email or log in with your password first to link accounts.",
        )
        # Immediately redirect to the normal login page
        raise self._immediate_http_response(request, account_login)

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        """
        Redirect to a profile completion page if the user's profile is incomplete.
        """
        user = request.user
        # Your User model requires 'birth' and 'gender'.
        if not getattr(user, 'birth', None) or not getattr(user, 'gender', None):
            # Assuming you have a URL named 'complete_profile'.
            # You can change '/complete-profile/' to `reverse('complete_profile')`
            return '/complete-profile/'
        
        # Otherwise, use the default redirect URL from settings
        return super().get_login_redirect_url(request)
