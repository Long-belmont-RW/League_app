from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate

from .models import User, UserProfile

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'

class UserRegistriationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role_coach = forms.BooleanField(required=False, label="Register as Coach")
    role_player = forms.BooleanField(required=False, label="Register as Player")
    role_fan = forms.BooleanField(required=False, label="Register as Fan", initial=True)

    class Meta:
        model = User

        fields = ('username', 'email', 'birth', 'gender', 'password1', 'password2')

    
    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email
    
    

    
    def clean(self):
        cleaned_data = super().clean()
        # Ensure at least one role is selected
        if not any([cleaned_data.get('role_coach'), 
                   cleaned_data.get('role_player'), 
                   cleaned_data.get('role_fan')]):
            raise forms.ValidationError("Please select at least one role.")
        return cleaned_data

    def save(self, commit=True):
        user =  super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_coach = self.cleaned_data.get('role_coach', False)
        user.is_player = self.cleaned_data.get('role_player', False)
        user.is_fan = self.cleaned_data.get('role_fan', True)

        if commit:
            user.save()
        return user
