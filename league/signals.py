# league/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PlayerStats, Match, TeamSeasonParticipation, MatchStatus
from django.db.models import Q, F

@receiver([post_save, post_delete], sender=PlayerStats)
def update_player_season_stats(sender, instance, **kwargs):
    """ Update player season stats after player stats are saved or deleted.
    This updates the player's participation record with total goals, assists,
    and other relevant statistics."""
    
    participation = instance.player_participation
    if participation:
        participation.update_totals()


@receiver([post_save, post_delete], sender=Match)
def update_team_season_stats(sender, instance, **kwargs):
    """ Update team season stats after a match is saved or deleted.
    This calculates wins, losses, draws, points, goals scored, and goals conceded
    for each team in the league of the match."""

    league = instance.season
    # Get all teams participating in this league
    team_participations = TeamSeasonParticipation.objects.filter(league=league)
    for team_sea_par in team_participations:
        team = team_sea_par.team
        matches = Match.objects.filter(season=league, status=MatchStatus.FINISHED).filter(
            Q(home_team=team) | Q(away_team=team)
        )
        wins = losses = draws = points = goals_scored = goals_conceded = matches_played = 0
        for match in matches:
            is_home = match.home_team == team
            home_goals = match.home_score
            away_goals = match.away_score
            scored = home_goals if is_home else away_goals
            conceded = away_goals if is_home else home_goals
            goals_scored += scored
            goals_conceded += conceded
            matches_played += 1
            if home_goals > away_goals:
                if is_home:
                    wins += 1
                    points += 3
                else:
                    losses += 1
            elif home_goals < away_goals:
                if is_home:
                    losses += 1
                else:
                    wins += 1
                    points += 3
            else:
                draws += 1
                points += 1
        team_sea_par.wins = wins
        team_sea_par.losses = losses
        team_sea_par.draws = draws
        team_sea_par.points = points
        team_sea_par.goals_scored = goals_scored
        team_sea_par.goals_conceded = goals_conceded
        team_sea_par.matches_played = matches_played
        team_sea_par.save(update_fields=[
            'wins', 'losses', 'draws', 'points', 'goals_scored', 'goals_conceded', 'matches_played'
        ])
       