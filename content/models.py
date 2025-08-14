from django.db import models
from django.utils import timezone


from users.models import User
from league.models import Team

import uuid
from datetime import timedelta



def default_expiry():
    return timezone.now() + timedelta(days=3)


class Invitation(models.Model):
    """Stores a single-use invitation for a user to join a team with a specific role."""
    email = models.EmailField()
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=User.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')

    class Meta:
        indexes = [
            models.Index(fields=["email", "is_accepted", "expires_at"]),
        ]

    def is_expired(self):
        """Check if the invitation has expired."""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invitation for {self.email} to join {self.team.name}"