from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class MultiRoleAuthBackend(ModelBackend):
    def authenticate(self, request, username = None, password = None **kwargs):
        """Custom authentication to check if a role is selected"""

        user =  super().authenticate(request, username, password, **kwargs)

        if user:
            #Authenticate only if a user has a specified role
            if not any([user.is_fan, user.is_player, user.is_coach]):
                return None
        
        return User

class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, username = None, password = None, **kwargs):
        """custom email authentication"""
        try:
            #try to find user by email
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        return None
    
    def get_user(self, user_id):
        try: 
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
