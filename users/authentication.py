from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailMultiRoleAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find user by email
            user = User.objects.get(email=username)
            if user.check_password(password):
                # Multi-role logic: check if user has at least one active role
                if not any([user.is_fan, user.is_player, user.is_coach]) and not user.is_admin:
                    return None
                return user
        except User.DoesNotExist:
            return None
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None