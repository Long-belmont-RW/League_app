from django.test import TestCase, Client
from django.utils import timezone
from datetime import datetime, timedelta, time
from unittest.mock import patch
from django.urls import reverse

import pytest, pytz
from freezegun import freeze_time

from league.models import Team, League, Match, MatchStatus
from league.services import update_league_table



# @pytest.mark.django_db
# def test_league_table_calculation():
#     league = League.objects.create(year=2025, session="S")
#     team1 = Team.objects.create(name="Alpha FC")
#     team2 = Team.objects.create(name="Beta FC")

#     Match.objects.create(
#         season=league,
#         home_team=team1,
#         away_team=team2,
#         home_score=2,
#         away_score=1,
#         date="2025-06-01T15:00:00Z",
#         status=MatchStatus.FINISHED
#     )

#     update_league_table(league)

#     team1_participation = team1.teamseasonparticipation_set.get(league=league)
#     team2_participation = team2.teamseasonparticipation_set.get(league=league)

#     assert team1_participation.points == 3
#     assert team1_participation.wins == 1
#     assert team1_participation.goals_scored == 2

#     assert team2_participation.losses == 1
#     assert team2_participation.goals_conceded == 2



# class MatchListViewTests(TestCase):
#     def setUp(self):
#         self.client = Client()
#         self.league = League.objects.create(year=2025, session='S', is_active=True)
#         self.team1 = Team.objects.create(name="Team A")
#         self.team2 = Team.objects.create(name="Team B")
#         self.match1 = Match.objects.create(
#             season=self.league, home_team=self.team1, away_team=self.team2,
#             date='2025-07-15T10:00:00Z', status=MatchStatus.SCHEDULED, match_day=1
#         )
#         self.match2 = Match.objects.create(
#             season=self.league, home_team=self.team2, away_team=self.team1,
#             date='2025-07-14T10:00:00Z', status=MatchStatus.FINISHED,
#             home_score=2, away_score=1, match_day=1
#         )

#     def test_match_list_view(self):
#         response = self.client.get(reverse('match_list'))
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, "Scheduled Matches")
#         self.assertContains(response, "Finished Matches")
#         self.assertContains(response, f"{self.team1} vs {self.team2}")
#         self.assertContains(response, "2 - 1")

#     def test_team_filter(self):
#         response = self.client.get(reverse('match_list') + f'?team={self.team1.id}')
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, f"Showing matches for team: {self.team1}")
#         self.assertContains(response, f"{self.team1} vs {self.team2}")
#         self.assertNotContains(response, "No scheduled matches found")


class MatchModelTests(TestCase):
    """
    Test suite to test the implementation of the Match Model
    
    """

    @classmethod
    def setUp(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.league = League.objects.create(year=2024, session='S', is_active=True)
        cls.home_team = Team.objects.create(name="Home Team A")
        cls.away_team = Team.objects.create(name="Away Team B")

    def test_kickoff_time_not_set_for_scheduled(self):
        """
        Tests that actual kickoff time is not set when match status
        is 'SCHEDULED' 
        """
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED
        )
        self.assertIsNone(match.actual_kickoff_time)
        

    @freeze_time("2025-07-29 08:45:00")
    def test_kickoff_time_set_live(self):
        """
        Tests that actual_kickoff_time is set to timezone.now() when a match's
        status is updated from 'SCHEDULED' to 'LIVE'.
        """

        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED
        )
        self.assertIsNone(match.actual_kickoff_time)

        #Now change to live
        match.status = MatchStatus.LIVE
        match.save()

        #the kickoff time should be set to the frozen time
        self.assertEqual(match.actual_kickoff_time, timezone.now())


    @freeze_time("2025-07-29 09:00:00")
    def test_kickoff_time_is_not_overwritten(self):
        """
        Tests that the actual_kickoff_time is NOT updated if a mtach is already live
        and is saved again
        """

        #Create a live match
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=timezone.now(),
            status=MatchStatus.LIVE
        )

        initial_kickoff_time = match.actual_kickoff_time
        self.assertEqual(initial_kickoff_time, 
                        timezone.make_aware(timezone.datetime(2025, 7, 29, 9, 0, 0)))
        

        #freeze the time for 10 minutes and save the match
        with freeze_time("2025-07-29 09:10:00"):
            match.home_score = 1
            match.save()
        
        # The kickoff time should NOT have changed
        self.assertEqual(match.actual_kickoff_time, initial_kickoff_time)

    
    def test_get_current_minute_for_non_live_match(self):
        """
        Tests that get_current_minute() returns NONE for a match that is not live
        """

        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED
        )

        self.assertIsNone(match.get_current_minute())
        self.assertEqual(match.get_display_minute, "")

    
    @freeze_time("2025-07-29 10:00:00")
    def test_get_current_minute_at_halftime(self):
        """
        Tests get_current_minute() returns 45 for a match that kicked off 45 minutes ago
        """

        kickoff = timezone.now() - timedelta(minutes=45, seconds=30)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=kickoff,
        )

        self.assertEqual(match.get_current_minute(), 45)
        self.assertEqual(match.get_display_minute, "45'")


    @freeze_time("2025-07-29 11:00:00")
    def test_get_current_minute_in_extra_time(self):
        """
        Tests get_current_minute() and its display format for extra time.
        """
        kickoff = timezone.now() - timedelta(minutes=92)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=kickoff
        )
        self.assertEqual(match.get_current_minute(), 92)
        self.assertEqual(match.get_display_minute, "90 + 2'")

    
    @freeze_time("2025-07-29 12:00:00")
    def test_get_current_minute_at_90_minutes(self):
        """
        Tests that the display format is correct for exactly 90 minutes.
        """
        kickoff = timezone.now() - timedelta(minutes=90)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=kickoff
        )
        self.assertEqual(match.get_current_minute(), 90)
        self.assertEqual(match.get_display_minute, "90'")


    @freeze_time("2025-07-29 13:00:00")
    def test_get_current_minute_with_fallback_to_date(self):
        """
        Tests that get_current_minute() uses the scheduled 'date' field as a
        fallback if actual_kickoff_time is not set.
        """
        scheduled_date = timezone.now() - timedelta(minutes=25)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=scheduled_date,
            status=MatchStatus.LIVE,
            
        )

        match.actual_kickoff_time = None
        match.save()

        match.refresh_from_db()

        self.assertEqual(match.get_current_minute(), 25)
        self.assertEqual(match.get_display_minute, "25'")
        
    @freeze_time("2025-07-29 14:00:00")
    def test_get_current_minute_returns_zero_if_kickoff_is_in_future(self):
        """
        Tests that get_current_minute() returns 0 if the match is LIVE but the
        kickoff time is still in the future.
        """
        future_kickoff = timezone.now() + timedelta(minutes=10)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=future_kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=future_kickoff
        )
        self.assertEqual(match.get_current_minute(), 0)
        self.assertEqual(match.get_display_minute, "0'")
