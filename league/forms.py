from django import forms

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.db.models import Q, Sum
from .models import Match, PlayerStats, PlayerSeasonParticipation, Player, Lineup, MatchStatus, TeamSeasonParticipation, MatchEvent, LineupPlayer

from django.forms import BaseInlineFormSet
class MatchForm(forms.ModelForm):

    def clean(self):
        """Ensure home_score and away_score matches teh sum of goals scored by players"""
        cleaned_data = super().clean()
        home_team = cleaned_data.get('home_team')
        away_team = cleaned_data.get('away_team')
        season = cleaned_data.get('season')
        status = cleaned_data.get('status')
        
        # --- Validate that teams are active in the selected season ---
        if season and home_team:
            if not TeamSeasonParticipation.objects.filter(team=home_team, league=season).exists():
                self.add_error('home_team', f"{home_team} is not active in the {season} season.")
        
        if season and away_team:
            if not TeamSeasonParticipation.objects.filter(team=away_team, league=season).exists():
                self.add_error('away_team', f"{away_team} is not active in the {season} season.")


        # if cleaned_data.get('status') == MatchStatus.FINISHED:
        #     #get home and away scores
        #     home_score = cleaned_data.get('home_score', 0)
        #     away_score = cleaned_data.get('away_score', 0)
        #     match = self.instance

        #     if match.pk and status == MatchStatus.FINISHED:
        #         home_score = cleaned_data.get('home_score', 0)
        #         away_score = cleaned_data.get('away_score', 0)

        #         stats = PlayerStats.objects.filter(match=match)
        #         total_goals = stats.aggregate(total=Sum('goals'))['total'] or 0
        #         if total_goals != home_score + away_score:
        #             raise ValidationError("Total goals scored by players must match the sum of home and away scores.")
            
        return cleaned_data

      
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


# league/forms.py

class LineupPlayerForm(forms.ModelForm):
    # This new field will control whether a player is in the lineup or not.
    is_selected = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-indigo-500 bg-gray-700 border-gray-600 rounded focus:ring-indigo-600'
        })
    )

    def __init__(self, *args, **kwargs):
        self.eligible_ids = set(kwargs.pop('eligible_ids', []) or [])
        super().__init__(*args, **kwargs)

    class Meta:
        model = LineupPlayer
        # We only need `is_starter` from the model now.
        fields = ['player', 'is_starter']
        widgets = {
            # Player will be a hidden input; we'll display the name manually.
            'player': forms.HiddenInput(),
            'is_starter': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-500 bg-gray-700 border-gray-600 rounded focus:ring-indigo-600'
            }),
        }

    @property
    def player_obj(self):
        """Return the Player instance referenced by this form's player field for display in templates."""
        p = self.initial.get('player')
        if isinstance(p, Player):
            return p
        # If initial contained a PK (e.g., from POST re-render), try resolving it
        try:
            if p:
                return Player.objects.get(pk=p)
        except Player.DoesNotExist:
            pass
        # Try from bound data
        key = self.add_prefix('player')
        pk = self.data.get(key)
        try:
            if pk:
                return Player.objects.get(pk=pk)
        except Player.DoesNotExist:
            return None
        return None

    def clean(self):
        cleaned = super().clean()
        player = cleaned.get('player')
        # Validate the hidden player input belongs to the eligible roster
        if player and self.eligible_ids and player.id not in self.eligible_ids:
            raise ValidationError("Selected player is not eligible for this lineup.")
        return cleaned



class ValidatingLineupFormSet(BaseInlineFormSet):
    REQUIRED_STARTERS = 11  # enforce exactly 11 starters

    def clean(self):
        super().clean()
        starters = 0
        seen_players = set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            # Skip forms with errors so we don't KeyError
            if form.errors:
                continue
            is_selected = form.cleaned_data.get('is_selected', False)
            player = form.cleaned_data.get('player')
            is_starter = form.cleaned_data.get('is_starter', False)
            if not player:
                continue
            # prevent duplicate players in POST tampering
            if player.id in seen_players:
                raise ValidationError("Each player can only appear once in the lineup.")
            seen_players.add(player.id)
            if is_selected and is_starter:
                starters += 1
        if starters != self.REQUIRED_STARTERS:
            raise ValidationError(f"You must select exactly {self.REQUIRED_STARTERS} starters.")

# CREATE the formset factory
LineupFormSet = forms.inlineformset_factory(
    Lineup,                      # Parent model
    LineupPlayer,                # The 'through' model
    form=LineupPlayerForm,       # The form for each item in the set
    fields=('player', 'is_starter'),
    extra=0,                     # No extra empty forms
    can_delete=True,             # Allow removing players from the lineup
    formset=ValidatingLineupFormSet
)
class MatchEventForm(forms.ModelForm):
    class Meta:
        model = MatchEvent
        fields = ['player', 'event_type', 'commentary']
        widgets = {
            'player': forms.Select(attrs={
                'class': 'bg-gray-700 border border-gray-600 text-white text-sm rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-4 pr-4 py-3'
            }),
            'event_type': forms.Select(attrs={
                'class': 'bg-gray-700 border border-gray-600 text-white text-sm rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-4 pr-4 py-3'
            }),
            'commentary': forms.Textarea(attrs={
                'class': 'bg-gray-700 border border-gray-600 text-white text-sm rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-4 pr-4 py-3',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        match = kwargs.pop('match', None)
        super().__init__(*args, **kwargs)

        if match:
            # Get players from both home and away lineups
            home_lineup = Lineup.objects.filter(match=match, team=match.home_team).first()
            away_lineup = Lineup.objects.filter(match=match, team=match.away_team).first()
            
            player_ids = []
            if home_lineup:
                player_ids.extend(home_lineup.players.values_list('id', flat=True))
            if away_lineup:
                player_ids.extend(away_lineup.players.values_list('id', flat=True))

            self.fields['player'].queryset = Player.objects.filter(id__in=player_ids)




class PlayerForm(forms.ModelForm):
    pass