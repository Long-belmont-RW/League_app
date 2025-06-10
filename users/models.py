from django.db import models
from django.contrib.auth.models import AbstractUser
from league.models import Player, Coach

from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

class GenderChoices(models.TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'
    


class User(AbstractUser):
    email = models.EmailField(unique=True) #Email would be unique
    birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GenderChoices.choices, default=GenderChoices.MALE)
    is_coach = models.BooleanField(default=False)
    is_player = models.BooleanField(default=False)
    is_fan = models.BooleanField(default=True)

    USERNAME_FIELD = 'email' #email would be used for authentication
    REQUIRED_FIELDS = ['username', 'gender', 'birth']

    
    def age(self):
        if not self.birth:
            return "Age not provided"
        today = date.today()
        age = relativedelta(today, self.birth)
        return f"{age.years} years {age.months} months {age.days} days"

    def __str__(self):
        return self.username
    
    def clean(self):
        if self.birth and self.birth > date.today():
           raise ValidationError({'birth': 'Birth date cannot be in the future'})


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,)
    bio = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='coach_profiles/', blank=True, null=True)

    coach = models.OneToOneField(Coach, on_delete=models.SET_NULL, null=True, blank=True)
    player = models.OneToOneField(Player, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Profile"
    

    @property
    def roles(self):
        """Return a list of user's active roles"""
        roles = []

        if self.user.is_fan:
            roles.append('Fan')
        
        if self.user.is_player:
            roles.append('Fan')
        
        if self.user.is_coach:
            roles.append('Fan')
        
        return roles



