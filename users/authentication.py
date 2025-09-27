# accounts/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class EmailRoleAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email
    and checks for a specific role.

    It also enforces unique-email semantics during authentication:
    - Email matching is case-insensitive.
    - If multiple users share the same email, authentication fails to avoid ambiguity,
      unless exactly one account matches the provided password and role.
    - You should still enforce a database-level unique constraint on the email field
      in your User model to prevent duplicates in the first place.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Accept either 'username' or an explicit 'email' kwarg as the email input
        email = (kwargs.get('email') or username or '').strip()
        if not email or not password:
            return None

        # Case-insensitive lookup; fetch all candidates with this email
        candidates = list(User._default_manager.filter(email__iexact=email))

        if not candidates:
            return None

        # If duplicates exist, fail closed unless exactly one matches password+role
        if len(candidates) > 1:
            matched = []
            for u in candidates:
                # Respect ModelBackend's user_can_authenticate (e.g., is_active)
                if not self.user_can_authenticate(u):
                    continue
                try:
                    if u.check_password(password) and getattr(u, 'role', None):
                        matched.append(u)
                except Exception:
                    # Defensive: never raise from the auth path
                    continue

            if len(matched) == 1:
                logger.warning(
                    "Duplicate email detected for %s; authenticated deterministically by password+role match. "
                    "Please enforce a unique email constraint.",
                    email,
                )
                return matched[0]

            logger.error(
                "Duplicate email detected for %s; authentication aborted to enforce unique email semantics.",
                email,
            )
            return None

        # Exactly one candidate
        user = candidates[0]
        if not self.user_can_authenticate(user):
            return None
        if user.check_password(password) and getattr(user, 'role', None):  # User must select a role
            return user
        return None

    def get_user(self, user_id):
        try:
            user = User._default_manager.get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
