# league/utils.py
from django.db import models
from .models import TeamSeasonParticipation

from django.db.models import F
from .models import TeamSeasonParticipation

def get_league_standings(league):
    """
    Generate league standings for a given league, sorted by points, goal difference, and goals scored.
    Returns a list of dictionaries with team data and calculated fields.
    """
    teams = TeamSeasonParticipation.objects.filter(league=league).select_related('team')
    standings = []
    for position, team in enumerate(teams, start=1):
        standings.append({
            'position': position,
            'team': team.team,
            'matches_played': team.matches_played,
            'wins': team.wins,
            'draws': team.draws,
            'losses': team.losses,
            'goals_scored': team.goals_scored,
            'goals_conceded': team.goals_conceded,
            'goal_difference': team.goal_difference,  # Use property directly
            'points': team.points,
        })
    return sorted(
        standings,
        key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
        reverse=True
    )