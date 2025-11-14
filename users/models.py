from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from league.models import Player, Coach

from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
import time
import os


def user_profile_image_upload_to(instance, filename):
    """Create a unique filename for a user's profile image.

    Example: user_12_1700000000.jpg
    """
    base, ext = os.path.splitext(filename)
    timestamp = int(time.time())
    user_id = getattr(instance.user, 'id', 'anon')
    return f'user_profiles/user_{user_id}_{timestamp}{ext}'

class GenderChoices(models.TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'
    

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        username = extra_fields.get("username")
        if not username:
            username = email.split("@")[0]
            extra_fields["username"] = username
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


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
    


    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        # Ensure staff flag is consistent with privileges/role
        if self.is_superuser:
            self.is_staff = True
        else:
            self.is_staff = (self.role == 'admin')
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
    image = models.ImageField(upload_to=user_profile_image_upload_to, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    coach = models.OneToOneField(Coach, on_delete=models.SET_NULL, null=True, blank=True)
    player = models.OneToOneField(Player, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Fans can follow multiple teams
    favorite_teams = models.ManyToManyField('league.Team', blank=True, related_name='followers')

    def __str__(self):
        return f"{self.user.username} - Profile"
    

    @property
    def role(self):
        return self.user.role.capitalize()


class Notification(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    match = models.ForeignKey('league.Match', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification to {self.user.email}: {self.title}"