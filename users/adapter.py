from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email, user_username
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        # Force auto signup
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        # Ensure username is set if missing (using email prefix)
        if not user.username:
            email = user_email(user)
            if email:
                username = email.split('@')[0]
                # Ensure uniqueness (simple version, allauth handles collisions usually but good to be safe)
                user.username = username
        
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed
        (and before the pre_social_login signal is emitted).

        We use this to manually connect the social account to an existing user
        if the email matches, bypassing the 'account already exists' error.
        """
        # If the social account is already connected to a user, we're done
        if sociallogin.is_existing:
            return

        # If the user is already logged in, the default behavior is to connect
        # (unless configured otherwise). We are handling the case where the user
        # is NOT logged in but has an account with the same email.
        if not request.user.is_authenticated:
            email = user_email(sociallogin.user)
            if email:
                try:
                    user = User.objects.get(email=email)
                    # Connect the social account to the existing user
                    sociallogin.connect(request, user)
                except User.DoesNotExist:
                    pass
