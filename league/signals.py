from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_added
from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(user_signed_up)
def populate_profile_on_signup(request, user, **kwargs):
    """
    When a new user signs up via a social account, populate their profile
    with the data from the social provider.
    """
    sociallogin = kwargs.get('sociallogin')
    if sociallogin:
        _populate_user_profile(sociallogin, user)

@receiver(social_account_added)
def populate_profile_on_connect(request, sociallogin, **kwargs):
    """
    When a social account is connected to an existing user, populate their
    profile with the data from the social provider.
    """
    if sociallogin:
        _populate_user_profile(sociallogin, sociallogin.user)

def _populate_user_profile(sociallogin, user):
    """
    Helper function to populate user model fields from social account data.
    """
    if sociallogin.account.provider == 'google':
        extra_data = sociallogin.account.extra_data
        # Only update if the local field is empty
        if not user.first_name and 'given_name' in extra_data:
            user.first_name = extra_data['given_name']
        if not user.last_name and 'family_name' in extra_data:
            user.last_name = extra_data['family_name']
        user.save()

    if sociallogin.account.provider == 'github':
        extra_data = sociallogin.account.extra_data
        if not user.first_name and 'name' in extra_data:
            # GitHub often provides the full name in a single 'name' field.
            # We'll attempt to split it.
            name_parts = extra_data['name'].split()
            if len(name_parts) > 0:
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = ' '.join(name_parts[1:])
        user.save()
