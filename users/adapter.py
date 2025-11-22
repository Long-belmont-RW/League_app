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
