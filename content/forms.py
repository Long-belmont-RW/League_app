from django import forms

from .models import *

class CoachInvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email', 'team']

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['team'].queryset = Team.objects.all()
        self.fields['team'].label = 'Assign to Team'
        self.fields['email'].widget.attrs.update({'placeholder': 'Enter coach email'})

class PlayerInvitationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter player email',
            'class': 'w-full px-3 py-2 text-white bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
        