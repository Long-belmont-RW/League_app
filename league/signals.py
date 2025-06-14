from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PlayerStats, Match, TeamSeasonParticipation
from django.db.models import Q

@receiver([post_save, post_delete], sender=PlayerStats)
def update_player_season_stats(sender, instance, **kwargs):
    player_participation = instance.player_participation
    player_participation.update_totals()

@receiver([post_save, post_delete], sender=Match)
def update_team_season_stats(sender, instance, **kwargs):
    league = instance.season

    # Process EACH team separately
    for team in [instance.home_team, instance.away_team]:
        team_sea_par, _ = TeamSeasonParticipation.objects.get_or_create(
            team=team, 
            league=league
        )

        # Get all matches for THIS SPECIFIC team in this league
        matches = Match.objects.filter(season=league).filter(
            Q(home_team=team) | Q(away_team=team)
        )

        # Initialize counters for THIS team
        goals_scored = 0
        goals_conceded = 0
        wins = 0
        losses = 0
        draws = 0
        points = 0

        # Calculate stats for THIS team from all their matches
        for match in matches:
            if match.home_team == team:
                gs, gc = match.home_score, match.away_score
            else:
                gs, gc = match.away_score, match.home_score

            goals_scored += gs
            goals_conceded += gc

            if gs > gc:
                wins += 1
                points += 3
            elif gs == gc:
                points += 1
                draws += 1
            else:
                losses += 1

        # Update THIS team's season participation record
        team_sea_par.goals_scored = goals_scored
        team_sea_par.goals_conceded = goals_conceded
        team_sea_par.wins = wins
        team_sea_par.losses = losses  
        team_sea_par.draws = draws   
        team_sea_par.matches_played = matches.count()
        team_sea_par.save()