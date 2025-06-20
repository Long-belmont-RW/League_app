from django.test import TestCase

import pytest
from league.models import Team, League, Match, MatchStatus
from league.services import update_league_table

@pytest.mark.django_db
def test_league_table_calculation():
    league = League.objects.create(year=2025, session="S")
    team1 = Team.objects.create(name="Alpha FC")
    team2 = Team.objects.create(name="Beta FC")

    Match.objects.create(
        season=league,
        home_team=team1,
        away_team=team2,
        home_score=2,
        away_score=1,
        date="2025-06-01T15:00:00Z",
        status=MatchStatus.FINISHED
    )

    update_league_table(league)

    team1_participation = team1.teamseasonparticipation_set.get(league=league)
    team2_participation = team2.teamseasonparticipation_set.get(league=league)

    assert team1_participation.points == 3
    assert team1_participation.wins == 1
    assert team1_participation.goals_scored == 2

    assert team2_participation.losses == 1
    assert team2_participation.goals_conceded == 2

