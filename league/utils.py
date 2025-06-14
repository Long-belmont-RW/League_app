# league/utils.py
from django.db import models
from .models import TeamSeasonParticipation

def get_league_standings(league):
    """
    Returns a ranked list of teams for a given league, sorted by:
    - Points (desc)
    - Goal difference (desc)
    - Goals scored (desc)
    """

    # Get all teams in the league, with optional annotations if needed
    teams = TeamSeasonParticipation.objects.filter(league=league).annotate(
        goal_difference=models.F('goals_scored') - models.F('goals_conceded')
    ).order_by(
        '-points',               # Highest points first
        '-goal_difference',      # Then highest goal difference
        '-goals_scored'          # Then most goals scored
    )

    standings = []
    for position, team in enumerate(teams, start=1):
        standings.append({
            'position': position,
            'team': team.team.name,
            'points': team.points,
            'goal_difference': team.goal_difference,
            'goals_scored': team.goals_scored,
            'goals_conceded': team.goals_conceded,
            'wins': team.wins,
        })

    return standings
