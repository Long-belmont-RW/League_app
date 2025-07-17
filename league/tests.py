from django.test import TestCase, Client
from django.urls import reverse

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



class MatchListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.league = League.objects.create(year=2025, session='S', is_active=True)
        self.team1 = Team.objects.create(name="Team A")
        self.team2 = Team.objects.create(name="Team B")
        self.match1 = Match.objects.create(
            season=self.league, home_team=self.team1, away_team=self.team2,
            date='2025-07-15T10:00:00Z', status=MatchStatus.SCHEDULED, match_day=1
        )
        self.match2 = Match.objects.create(
            season=self.league, home_team=self.team2, away_team=self.team1,
            date='2025-07-14T10:00:00Z', status=MatchStatus.FINISHED,
            home_score=2, away_score=1, match_day=1
        )

    def test_match_list_view(self):
        response = self.client.get(reverse('match_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scheduled Matches")
        self.assertContains(response, "Finished Matches")
        self.assertContains(response, f"{self.team1} vs {self.team2}")
        self.assertContains(response, "2 - 1")

    def test_team_filter(self):
        response = self.client.get(reverse('match_list') + f'?team={self.team1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Showing matches for team: {self.team1}")
        self.assertContains(response, f"{self.team1} vs {self.team2}")
        self.assertNotContains(response, "No scheduled matches found")