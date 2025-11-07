from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from league.models import Coach, Player, Team
from .models import User, UserProfile  # Assuming User extends AbstractUser

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'birth', 'gender', 'role')

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['role'].choices = [choice for choice in self.fields['role'].choices if choice[0] != 'admin']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Improve UX: use date picker for birth
        if 'birth' in self.fields:
            try:
                self.fields['birth'].widget.input_type = 'date'
            except Exception:
                pass


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['birth', 'gender']
        widgets = {
            'birth': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth'].required = True
        self.fields['gender'].required = True
        # Accept common input formats while displaying as YYYY-MM-DD
        self.fields['birth'].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']


class UserAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'birth', 'gender']
        widgets = {
            'birth': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Accept common input formats while displaying as YYYY-MM-DD
        self.fields['birth'].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'image', 'favorite_teams']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'favorite_teams': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order teams for nicer UX and make selection optional
        self.fields['favorite_teams'].queryset = Team.objects.all().order_by('name')
        self.fields['favorite_teams'].required = False


class PlayerCreationForm(forms.ModelForm):
    position = forms.ChoiceField(choices=Player.POSITION_CHOICES, required=True)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'birth', 'gender']
        widgets = {
            'birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True


    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
