from django import forms

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.db.models import Q
from .models import Match, PlayerStats, PlayerSeasonParticipation


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['season', 'home_team', 'home_score', 'away_team', 'away_score', 'date', 'status']
        widgets = {
            'date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'season': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            }),
            'match_day': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'min': '1',
                'max': '10',  # Assuming a maximum of 10 match days
                'placeholder': 'Match Day (1-8)',
            }),
            'home_team': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            }),
            'away_team': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            }),
            'home_score': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'min': '0'
            }),
            'away_score': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'min': '0'
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for datetime-local input if editing
        if self.instance and self.instance.pk and self.instance.date:
            self.initial['date'] = self.instance.date.strftime('%Y-%m-%dT%H:%M')
       
    
    def clean_date(self):
        """Prevents selecting a date in the past (unless editing existing match)"""
        date = self.cleaned_data.get("date")
        if date:
            # Allow past dates when editing existing matches
            if not self.instance.pk and date < timezone.now():
                raise ValidationError("Match date cannot be in the past")
        return date
    

class PlayerStatsForm(forms.ModelForm):
    """Individual player stats form with enhanced validation and styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make player field read-only but visible
        if self.instance and self.instance.pk:
            self.fields['player'].disabled = True
            self.fields['player'].widget.attrs.update({
                'class': 'block w-full bg-gray-50 border-gray-300 rounded-md shadow-sm sm:text-sm cursor-not-allowed'
            })
    
    class Meta:
        model = PlayerStats
        fields = ['player', 'goals', 'assists', 'yellow_cards', 'red_cards']
        widgets = {
            'player': forms.Select(attrs={
                'class': 'block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'goals': forms.NumberInput(attrs={
                'class': 'w-16 text-center border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'min': '0',
                'max': '20'  # Reasonable maximum
            }),
            'assists': forms.NumberInput(attrs={
                'class': 'w-16 text-center border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'min': '0',
                'max': '20'
            }),
            'yellow_cards': forms.NumberInput(attrs={
                'class': 'w-16 text-center border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'min': '0',
                'max': '2'  # Maximum 2 yellow cards per player per match
            }),
            'red_cards': forms.NumberInput(attrs={
                'class': 'w-16 text-center border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm',
                'min': '0',
                'max': '1'  # Maximum 1 red card per player per match
            })
        }
    
    def clean_yellow_cards(self):
        """Validate yellow cards count"""
        yellow_cards = self.cleaned_data.get('yellow_cards', 0)
        if yellow_cards > 2:
            raise ValidationError("A player cannot receive more than 2 yellow cards in a match")
        return yellow_cards
    
    def clean_red_cards(self):
        """Validate red cards count"""
        red_cards = self.cleaned_data.get('red_cards', 0)
        if red_cards is None:
            red_cards=0
        if red_cards > 1:
            raise ValidationError("A player cannot receive more than 1 red card in a match")
        return red_cards
    
    def clean_goals(self):
        goals = self.cleaned_data.get('goals')
        if goals is None:
            goals=0

        if goals < 0:
            raise forms.ValidationError("Goals cannot be negative.")
        return goals
    
    def clean_assists(self):
        assists = self.cleaned_data.get('assists')
        if assists is None:
            assists=0

        if assists < 0:
            raise forms.ValidationError("assists cannot be negative.")
        return assists



   
# Enhanced formset with better configuration
PlayerStatsFormSet = forms.modelformset_factory(
    PlayerStats,
    form=PlayerStatsForm,
    fields=['player', 'goals', 'assists', 'yellow_cards', 'red_cards'],
    extra=0,
    can_delete=False,
    # validate_min=False,
    # validate_max=False
)