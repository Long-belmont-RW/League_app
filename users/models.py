from django.db import models
from django.contrib.auth.models import AbstractUser
from league.models import Player, Coach


class User(AbstractUser):
    is_coach = models.BooleanField(default=False)
    is_player = models.BooleanField(default=False)
    is_fan = models.BooleanField(default=True)

    def __str__(self):
        return self.username


class CoachProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'is_coach': True})
    bio = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='coach_profiles/', blank=True, null=True)
    coach = models.OneToOneField(Coach, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Coach Profile"


class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'is_player': True})
    bio = models.TextField(blank=True, null=True)
    img = models.ImageField(upload_to='player_profiles/', blank=True, null=True)
    player = models.OneToOneField(Player, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Player Profile"


class FanProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'is_fan': True})
    bio = models.TextField(blank=True, null=True)
    img = models.ImageField(upload_to='fan_profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - Fan Profile"
