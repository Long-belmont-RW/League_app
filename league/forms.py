from django import forms
from django.utils import timezone
from league.models import Match
from django.core.exceptions import ValidationError

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['season', 'home_team', 'away_team', 'date', 'status']
        widgets = {
            'date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set initial value for datetime-local input if editing
        if self.instance and self.instance.pk and self.instance.date:
            self.initial['date'] = self.instance.date.strftime('%Y-%m-%dT%H:%M')
    
    def clean_date(self):
        """Prevents selecting a date in the past"""
        date = self.cleaned_data.get("date")
        if date and date < timezone.now():
            raise forms.ValidationError("Match date cannot be in the past")
        return date
    
