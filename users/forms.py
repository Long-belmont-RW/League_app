from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from league.models import Coach
from .models import User, UserProfile  # Assuming User extends AbstractUser

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ('username', 'email', 'birth', 'gender', 'role')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # get request context for role filtering
        super().__init__(*args, **kwargs)

        if self.request and not (self.request.user.is_authenticated and self.request.user.role == 'admin'):
            # Remove 'admin' from choices for non-admins
            allowed_choices = [choice for choice in User.ROLE_CHOICES if choice[0] != 'admin']
            self.fields['role'].choices = allowed_choices

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role == 'admin':
            if not (self.request and self.request.user.is_authenticated and self.request.user.role == 'admin'):
                raise forms.ValidationError("Only admins can register admin accounts.")
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']

        # Set is_staff based on role
        user.is_staff = (user.role == 'admin')
        if commit:
            user.save()
        return user

class InvitationRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'birth', 'gender')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # In the context of an invitation, the user shouldn't exist with this email.
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # The role will be set in the view from the invitation object.
        if commit:
            user.save()
        return user
