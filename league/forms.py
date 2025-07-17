from django import forms

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.db.models import Q, Sum
from .models import Match, PlayerStats, PlayerSeasonParticipation, Player, Lineup, MatchStatus


class MatchForm(forms.ModelForm):

    def clean(self):
        """Ensure home_score and away_score matches teh sum of goals scored by players"""
        cleaned_data = super().clean()
        if cleaned_data.get('status') == 'FIN':
            #get home and away scores
            home_score = cleaned_data.get('home_score', 0)
            away_score = cleaned_data.get('away_score', 0)
            match = self.instance

            if match.pk:
                stats = PlayerStats.objects.filter(match=match)
                total_goals = stats.aggregate(total=Sum('goals'))['total'] or 0
                if home_score + away_score != total_goals:
                    raise ValidationError("Total goals scored by players must match the sum of home and away scores.")
            
        return cleaned_data

        # Get all player stats for this match
        player_stats = PlayerStats.objects.filter(match=self.instance)

        # Calculate total goals scored by players
        total_goals = sum(stat.goals for stat in player_stats)

        if home_score + away_score != total_goals:
            raise ValidationError("Total goals scored by players must match the sum of home and away scores.")
    class Meta:
        model = Match
        fields = ['season','match_day', 'home_team', 'home_score', 'away_team', 'away_score', 'date', 'status']
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
        self.match = kwargs.pop('match', None)
        super().__init__(*args, **kwargs)

        #Get only active players in the match's league
        if self.match:
            active_players = PlayerSeasonParticipation.objects.filter(
                league=self.match.season, is_active=True,
                team__in=[self.match.home_team, self.match.away_team]
            ).values_list('player_id', flat=True)

            self.fields['player'].queryset = Player.objects.filter(id__in=active_players)

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


class LineupForm(forms.ModelForm):
    """Form for creating/editing lineups with enhanced validation and styling"""
    
    def __init__(self, *args, **kwargs):
        self.match = kwargs.pop('match', None)
        super().__init__(*args, **kwargs)

        # Get only active players in the match's league
        if self.match:
            active_players = PlayerSeasonParticipation.objects.filter(
                league=self.match.season, is_active=True,
                team__in=[self.match.home_team, self.match.away_team]
            ).values_list('player_id', flat=True)

            self.fields['players'].queryset = Player.objects.filter(id__in=active_players)

    class Meta:
        model = Lineup
        fields = ['team', 'players',]
        widgets = {
            'players': forms.SelectMultiple(attrs={
                'class': 'block w-full border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            })
        }