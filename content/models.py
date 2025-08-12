from django.db import models
from django.utils import timezone


from users.models import User
from league.models import Team, Player, League

import uuid
from datetime import timedelta



class Invitation(models.Model):
    """Stores a single-use invitation to a user (coach) to join a team"""
    email = models.EmailField(unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=User.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')


    def is_expired(self):
        """Check if the invitation has expired (e.g., after 3 days)"""
        return timezone.now() > self.created_at + timedelta(days=3)


    def __str__(self):
        return f"Invitation for {self.email} to join {self.team.name}"