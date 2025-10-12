
<!-- Lineup_manager.html -->
{% extends 'base.html' %}
{% load static %}
{% load league_extras %}

{% block title %}Manage Lineup - {{ match.home_team.name }} vs {{ match.away_team.name }}{% endblock %}

{% block content %}
<style>
    :root {
        --pitch-color: #53a157;
        --line-color: #c7d5c8;
        --player-card-bg: #f8f9fa;
        --player-card-border: #dee2e6;
        --sub-bench-bg: #e9ecef;
        --available-pool-bg: #f1f3f5;
    }
    .lineup-container {
        display: flex;
        gap: 2rem;
        align-items: flex-start;
    }
    .team-lineup-manager {
        flex: 1;
        min-width: 450px;
    }
    .pitch {
        background-color: var(--pitch-color);
        border: 2px solid var(--line-color);
        position: relative;
        width: 100%;
        aspect-ratio: 7 / 5;
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        padding: 1rem;
    }
    .pitch-row {
        display: flex;
        justify-content: space-around;
    }
    .player-slot {
        width: 70px;
        height: 90px;
        border: 2px dashed rgba(255, 255, 255, 0.5);
        border-radius: 5px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.2);
    }
    .player-card {
        width: 100%;
        height: 100%;
        padding: 0.25rem;
        background-color: var(--player-card-bg);
        border: 1px solid var(--player-card-border);
        border-radius: 4px;
        cursor: grab;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        font-size: 0.8rem;
    }
    .player-card .player-name {
        font-weight: bold;
    }
    .player-card .player-pos {
        font-size: 0.7rem;
        color: #6c757d;
    }
    .player-list-container {
        min-height: 100px;
        padding: 0.5rem;
        border-radius: 5px;
        margin-top: 1rem;
    }
    .substitutes-bench {
        background-color: var(--sub-bench-bg);
    }
    .available-players-pool {
        background-color: var(--available-pool-bg);
    }
    .player-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .player-list .player-slot {
        background: none;
        border: none;
    }
    .sortable-ghost {
        opacity: 0.4;
        background-color: #0d6efd;
    }
</style>

<div class="container-fluid mt-4">
    <h1 class="mb-4 text-center">Manage Lineup</h1>
    <h3 class="text-center">{{ match.home_team.name }} vs {{ match.away_team.name }}</h3>

    <div class="lineup-container">
        <!-- Home Team -->
        {% include 'lineup_partial.html' with team_context=home_team_context formations=formations team_type='home' %}
        
        <!-- Away Team -->
        {% include 'lineup_partial.html' with team_context=away_team_context formations=formations team_type='away' %}
    </div>
</div>

<!-- Player card template -->
<template id="player-card-template">
    <div class="player-card" data-player-id="">
        <div class="player-name"></div>
        <div class="player-pos"></div>
    </div>
</template>

{{ home_team_context.starters|json_script:"starters-data-"|add:home_team_context.team.id }}
{{ home_team_context.substitutes|json_script:"substitutes-data-"|add:home_team_context.team.id }}
{{ home_team_context.available_players|json_script:"available-data-"|add:home_team_context.team.id }}

{{ away_team_context.starters|json_script:"starters-data-"|add:away_team_context.team.id }}
{{ away_team_context.substitutes|json_script:"substitutes-data-"|add:away_team_context.team.id }}
{{ away_team_context.available_players|json_script:"available-data-"|add:away_team_context.team.id }}

{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
<script src="{% static 'js/lineup-manager.js' %}"></script>
{% endblock %}


<!-- League_extras.py -->
# league/templatetags/league_extras.py
from django import template

register = template.Library()

@register.filter(name='parse_formation')
def parse_formation(formation_str):
    """
    Parses a formation string like '4-4-2' into a list of lists for looping.
    Returns [[1, 2, 3, 4], [1, 2, 3, 4], [1, 2]] for '4-4-2'.
    """
    if not isinstance(formation_str, str) or not '-' in formation_str:
        return [] # Return empty list for invalid input
    try:
        parts = [int(p) for p in formation_str.split('-')]
        # We only care about defenders, midfielders, and forwards for the pitch grid rows
        rows = parts[:3]
        return [range(count) for count in rows]
    except (ValueError, TypeError):
        return [] # Return empty on parsing error


<!-- manage_lineup_view() -->

def manage_lineup_view(request, match_id):
    """
    View to create or edit lineups for a specific match.
    Refactored to simplify data fetching and improve performance.
    """
    match = get_object_or_404(Match.objects.select_related('home_team', 'away_team', 'season'), pk=match_id)
    user = request.user

    # --- Permission Checks ---
    is_admin = user.is_staff and getattr(user, 'role', None) == 'admin'
    is_home_coach = False
    is_away_coach = False

    # Check for coach role based on your UserProfile model
    if hasattr(user, 'userprofile') and hasattr(user.userprofile, 'coach') and user.userprofile.coach:
        coach = user.userprofile.coach
        is_home_coach = CoachSeasonParticipation.objects.filter(coach=coach, team=match.home_team, league=match.season).exists()
        is_away_coach = CoachSeasonParticipation.objects.filter(coach=coach, team=match.away_team, league=match.season).exists()

    if not (is_admin or is_home_coach or is_away_coach):
        raise PermissionDenied("You do not have permission to manage this lineup.")

    # --- POST Request Logic ---
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            team_id = data.get('team_id')
            
            # Ensure the user is authorized to edit this team's lineup
            if not (is_admin or (is_home_coach and int(team_id) == match.home_team.id) or (is_away_coach and int(team_id) == match.away_team.id)):
                 raise PermissionDenied("You are not authorized to modify this team's lineup.")

            starter_ids = data.get('starters', [])
            substitute_ids = data.get('substitutes', [])
            formation = data.get('formation', '4-4-2')

            lineup, _ = Lineup.objects.get_or_create(team_id=team_id, match=match)

            with transaction.atomic():
                # Clear existing players for this lineup
                lineup.lineupplayer_set.all().delete()

                # Create new LineupPlayer entries
                players_to_create = []
                for player_id in starter_ids:
                    players_to_create.append(LineupPlayer(lineup=lineup, player_id=player_id, is_starter=True))
                for player_id in substitute_ids:
                    players_to_create.append(LineupPlayer(lineup=lineup, player_id=player_id, is_starter=False))
                
                LineupPlayer.objects.bulk_create(players_to_create)

                # Update the formation
                lineup.formation = formation
                lineup.save()

            return JsonResponse({'status': 'success', 'message': 'Lineup saved successfully!'})
        except (KeyError, json.JSONDecodeError) as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid data provided: {str(e)}'}, status=400)
        except Exception as e:
            # Log the exception e
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

    # --- GET Request Logic ---
    def get_team_context(team):
        lineup, _ = Lineup.objects.get_or_create(team=team, match=match)
        
        # Fetch starters and substitutes in one query
        lineup_players = LineupPlayer.objects.filter(lineup=lineup).select_related('player')
        starters = [lp.player for lp in lineup_players if lp.is_starter]
        substitutes = [lp.player for lp in lineup_players if not lp.is_starter]
        
        lineup_player_ids = {p.id for p in starters} | {p.id for p in substitutes}

        # Get all active players for the team in the current season
        all_team_players = PlayerSeasonParticipation.objects.filter(
            team=team, 
            league=match.season,
            is_active=True
        ).select_related('player').distinct()

        # Determine available reserves
        reserves = [psp.player for psp in all_team_players if psp.player.id not in lineup_player_ids]

        return {
            'team': team,
            'lineup': lineup,
            'starters': starters,
            'substitutes': substitutes,
            'reserves': reserves,
            'formations': ['4-4-2', '4-3-3', '3-5-2', '4-2-3-1', '5-3-2'],
        }

    context = {
        'match': match,
        'home_context': get_team_context(match.home_team),
        'away_context': get_team_context(match.away_team),
        'save_lineup_url': reverse_lazy('manage_lineup', kwargs={'match_id': match.id}),
        'can_edit_home': is_admin or is_home_coach,
        'can_edit_away': is_admin or is_away_coach,
    }
    
    return render(request, 'league/manage_lineup_redesigned.html', context)


<!-- Snippet of my models.py -->

class LineupPlayer(models.Model):
    """Intermediary model to link a Player to a Lineup with extra data."""
    lineup = models.ForeignKey('Lineup', on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    is_starter = models.BooleanField(default=True, help_text="Is this player in the starting lineup?")
    
    class Meta:
        unique_together = ('lineup', 'player') # A player can only be in a lineup once
        ordering = ['-is_starter', 'player__last_name'] # Starters first

    def __str__(self):
        status = "Starter" if self.is_starter else "Substitute"
        return f"{self.player} ({status}) in {self.lineup.team.name} lineup"

# --- Lineup Model ---
class Lineup(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='lineups')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    players = models.ManyToManyField(Player, through='LineupPlayer', related_name='lineups')
    formation = models.CharField(max_length=10, blank=True, null=True, default='4-4-2')

    def __str__(self):
        return f"Lineup for {self.match} - {self.team}"

    def get_starters(self):
        return self.lineupplayer_set.filter(is_starter=True).select_related('player')

    def get_substitutes(self):
        return self.lineupplayer_set.filter(is_starter=False).select_related('player')



<!-- forms.py, some methods may be redundant. Look through though -->
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