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
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('player', 'Player'),
        ('coach', 'Coach'),
        ('fan', 'Fan'),
    )

    email = models.EmailField(unique=True)
    birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GenderChoices.choices, default=GenderChoices.MALE)

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='fan')
    created_at = models.DateTimeField(auto_now_add=True)
    


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'gender', 'birth']

    def save(self, *args, **kwargs):
        # Automatically set is_staff if user is an admin
        self.is_staff = self.role == 'admin'
        super().save(*args, **kwargs)

    @property 
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
    image = models.ImageField(upload_to='user_profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    coach = models.OneToOneField(Coach, on_delete=models.SET_NULL, null=True, blank=True)
    player = models.OneToOneField(Player, on_delete=models.SET_NULL, null=True, blank=True)


    def __str__(self):
        return f"{self.user.username} - Profile"
    

    @property
    def role(self):
        return self.user.role.capitalize()
