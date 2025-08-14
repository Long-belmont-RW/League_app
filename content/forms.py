from django import forms
from .models import Invitation
from league.models import Team

class CoachInvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email', 'team']

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['team'].queryset = Team.objects.all()
        self.fields['team'].label = 'Assign to Team'
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Enter coach email',
            'class': 'bg-gray-700 border border-gray-600 text-white text-sm rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-4 pr-4 py-3'
        })
        self.fields['team'].widget.attrs.update({
            'class': 'bg-gray-700 border border-gray-600 text-white text-sm rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-4 pr-4 py-3'
        })

class PlayerInvitationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter player email',
            'class': 'bg-gray-700 border border-gray-600 text-white text-sm rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-4 pr-4 py-3'
        })
    )
        