from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from datetime import datetime, timedelta, time
from unittest.mock import patch
from django.urls import reverse
import json

import pytest, pytz
from freezegun import freeze_time

from django.test.client import RequestFactory
from league.views import TopStatsView

from league.models import (Team, League, Match, MatchStatus, 
        TeamSeasonParticipation, Coach, Player, 
        Lineup, CoachSeasonParticipation, PlayerSeasonParticipation, MatchEvent, LineupPlayer, PlayerStats)
from users.models import UserProfile, Notification
from league.services import update_league_table
from .forms import MatchEventForm, LineupFormSet, PlayerStatsFormSet


#Get the custom User model 
User = get_user_model()

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
            home_score=0,
            away_score=0,
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
            home_score=0,
            away_score=0,
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
            home_score=0,
            away_score=0,
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
            home_score=0,
            away_score=0,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED
        )

        self.assertIsNone(match.get_current_minute())
        self.assertEqual(match.get_display_minute, "")


    @freeze_time("2025-07-29 10:00:00")
    def test_get_current_minute_at_halftime(self):
        """
        Tests get_current_minute() returns 45 for a match that kicked off 45 minutes ago
        and get_display_minute returns "HT".
        """

        kickoff = timezone.now() - timedelta(minutes=45, seconds=30)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            home_score=0,
            away_score=0,
            date=kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=kickoff,
        )

        self.assertEqual(match.get_current_minute(), 45)
        self.assertEqual(match.get_display_minute, "HT")


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
            home_score=0,
            away_score=0,
            date=kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=kickoff,
        )
        self.assertEqual(match.get_current_minute(), 77) # 92 raw - 15 HT = 77 playing
        self.assertEqual(match.get_display_minute, "77'")

    
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
            home_score=0,
            away_score=0,
            date=kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=kickoff
        )
        self.assertEqual(match.get_current_minute(), 75) # 90 raw - 15 HT = 75 playing
        self.assertEqual(match.get_display_minute, "75'")


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
            home_score=0,
            away_score=0,
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
            home_score=0,
            away_score=0,
            date=future_kickoff,
            status=MatchStatus.LIVE,
            actual_kickoff_time=future_kickoff
        )
        self.assertEqual(match.get_current_minute(), 0)
        self.assertEqual(match.get_display_minute, "0'")



class SignalAndStatUpdateTests(TestCase):
    """Tests the automated logic for updating league tables via signals"""

    def setUp(self):
        """Set up a league, two teams, and their participation records."""
        self.league = League.objects.create(year=2025, session="S", is_active=True)
        self.team1 = Team.objects.create(name="Blue Dragons")
        self.team2 = Team.objects.create(name="Red Phoenix")

        # Create the participation records that store the stats
        self.team1_participation = TeamSeasonParticipation.objects.create(
            team=self.team1, league=self.league
        )
        self.team2_participation = TeamSeasonParticipation.objects.create(
            team=self.team2, league=self.league
        )

    def test_stats_update_correctly_when_match_is_finished(self):
        """
        Tests that when a match is saved as FINISHED, the stats for
        both teams are calculated and saved correctly.
        """
        # Create a finished match where team1 wins
        Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=self.team2,
            home_score=2,
            away_score=1,
            date=timezone.now(),
            status=MatchStatus.FINISHED
        )

        # Refresh the participation objects from the database to get the updated stats
        self.team1_participation.refresh_from_db()
        self.team2_participation.refresh_from_db()

        # Assertions for the winning team (Team 1)
        self.assertEqual(self.team1_participation.points, 3)
        self.assertEqual(self.team1_participation.wins, 1)
        self.assertEqual(self.team1_participation.matches_played, 1)
        self.assertEqual(self.team1_participation.goals_scored, 2)
        self.assertEqual(self.team1_participation.goals_conceded, 1)

        # Assertions for the losing team (Team 2)
        self.assertEqual(self.team2_participation.points, 0)
        self.assertEqual(self.team2_participation.losses, 1)
        self.assertEqual(self.team2_participation.matches_played, 1)

    def test_stats_revert_when_match_is_no_longer_finished(self):
        """
        Tests the "status reversion" case. If a finished match is changed
        back to 'Scheduled', the stats should be recalculated and reset.
        """
        # Create and save a finished match
        match = Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=self.team2,
            home_score=3,
            away_score=0,
            date=timezone.now(),
            status=MatchStatus.FINISHED
        )

        # Verify the initial stats update
        self.team1_participation.refresh_from_db()
        self.assertEqual(self.team1_participation.points, 3)
        self.assertEqual(self.team1_participation.wins, 1)


        # "Un-finish" the match by changing its status
        match.status = MatchStatus.SCHEDULED
        match.save()

        # Refresh the participation objects again and assert stats are reset
        self.team1_participation.refresh_from_db()
        self.team2_participation.refresh_from_db()

        # Assertions for Team 1 - stats should be back to zero
        self.assertEqual(self.team1_participation.points, 0)
        self.assertEqual(self.team1_participation.wins, 0)
        self.assertEqual(self.team1_participation.matches_played, 0)

        # Assertions for Team 2 - stats should remain zero
        self.assertEqual(self.team2_participation.points, 0)
        self.assertEqual(self.team2_participation.losses, 0)
        self.assertEqual(self.team2_participation.matches_played, 0)
    
    def test_deleting_finished_match_reverts_stats(self):
        """
        Tests that if a finished match is deleted entirely, the stats
        are correctly recalculated and reverted.
        """
        # Create and save a finished match
        match = Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=self.team2,
            home_score=1,
            away_score=1, # A draw
            date=timezone.now(),
            status=MatchStatus.FINISHED
        )

        # Verify initial stats
        self.team1_participation.refresh_from_db()
        self.assertEqual(self.team1_participation.points, 1)
        self.assertEqual(self.team1_participation.draws, 1)

        # Delete the match
        match.delete()

        # Refresh and assert stats are reset
        self.team1_participation.refresh_from_db()
        self.assertEqual(self.team1_participation.points, 0)
        self.assertEqual(self.team1_participation.draws, 0)


class LineupNotificationTests(TestCase):
    """Ensure players get in-app and email notifications when selection changes."""

    def setUp(self):
        self.league = League.objects.create(year=2025, session='S', is_active=True)
        self.team1 = Team.objects.create(name='Test Dragons')
        self.team2 = Team.objects.create(name='Test Knights')

        # Users and profiles
        self.user = get_user_model().objects.create_user(
            username='p1', email='p1@example.com', password='x', role='player'
        )
        self.profile = UserProfile.objects.get(user=self.user)

        # Participation
        self.psp = PlayerSeasonParticipation.objects.create(
            player=self.profile.player, team=self.team1, league=self.league
        )

        # Match and lineup
        self.match = Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=self.team2,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED,
        )
        self.lineup = Lineup.objects.create(match=self.match, team=self.team1)

        # Set a default from email for testing purposes
        from django.conf import settings
        if not hasattr(settings, 'DEFAULT_FROM_EMAIL'):
            settings.DEFAULT_FROM_EMAIL = 'test@example.com'

    @patch('users.signals.send_mail')
    def test_notification_created_on_add_and_remove(self, mock_send_mail):
        initial_count = Notification.objects.filter(user=self.user).count()

        # Add to lineup -> should notify and email
        LineupPlayer.objects.create(lineup=self.lineup, player=self.profile.player, is_starter=True)
        self.assertEqual(
            Notification.objects.filter(user=self.user).count(), initial_count + 1
        )
        self.assertTrue(
            Notification.objects.filter(user=self.user, title__icontains='lineup').exists()
        )

        # Remove from lineup -> should notify and email again
        LineupPlayer.objects.filter(lineup=self.lineup, player=self.profile.player).delete()
        self.assertEqual(
            Notification.objects.filter(user=self.user).count(), initial_count + 2
        )
        self.assertTrue(
            Notification.objects.filter(user=self.user, title__icontains='removed').exists()                          
        )
                                                                                                                      
        # Email + realtime called for both actions                                                                    
        self.assertEqual(mock_send_mail.call_count, 2)

class TestComprehensiveLeagueUpdate(TestCase):
    def setUp(self):
        self.league = League.objects.create(year=2025, session="S", is_active=True)
        self.team_a = Team.objects.create(name="Team A")
        self.team_b = Team.objects.create(name="Team B")
        self.team_c = Team.objects.create(name="Team C") # For a match not affecting A or B

        self.team_a_stats = TeamSeasonParticipation.objects.create(team=self.team_a, league=self.league)
        self.team_b_stats = TeamSeasonParticipation.objects.create(team=self.team_b, league=self.league)

        # Initial match (scheduled, should not affect stats)
        self.match1 = Match.objects.create(
            season=self.league,
            home_team=self.team_a,
            away_team=self.team_b,
            home_score=0,
            away_score=0,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED
        )

    def _refresh_stats(self):
        self.team_a_stats.refresh_from_db()
        self.team_b_stats.refresh_from_db()

    def _assert_initial_stats(self):
        self._refresh_stats()
        self.assertEqual(self.team_a_stats.points, 0)
        self.assertEqual(self.team_a_stats.wins, 0)
        self.assertEqual(self.team_a_stats.draws, 0)
        self.assertEqual(self.team_a_stats.losses, 0)
        self.assertEqual(self.team_a_stats.goals_scored, 0)
        self.assertEqual(self.team_a_stats.goals_conceded, 0)
        self.assertEqual(self.team_a_stats.matches_played, 0)

        self.assertEqual(self.team_b_stats.points, 0)
        self.assertEqual(self.team_b_stats.wins, 0)
        self.assertEqual(self.team_b_stats.draws, 0)
        self.assertEqual(self.team_b_stats.losses, 0)
        self.assertEqual(self.team_b_stats.goals_scored, 0)
        self.assertEqual(self.team_b_stats.goals_conceded, 0)
        self.assertEqual(self.team_b_stats.matches_played, 0)

    def test_full_match_lifecycle_updates_league_correctly(self):
        self._assert_initial_stats()

        # 1. Change match to FINISHED (Team A wins 2-1)
        self.match1.home_score = 2
        self.match1.away_score = 1
        self.match1.status = MatchStatus.FINISHED
        self.match1.save()

        self._refresh_stats()
        self.assertEqual(self.team_a_stats.points, 3)
        self.assertEqual(self.team_a_stats.wins, 1)
        self.assertEqual(self.team_a_stats.goals_scored, 2)
        self.assertEqual(self.team_a_stats.goals_conceded, 1)
        self.assertEqual(self.team_a_stats.matches_played, 1)

        self.assertEqual(self.team_b_stats.points, 0)
        self.assertEqual(self.team_b_stats.losses, 1)
        self.assertEqual(self.team_b_stats.goals_scored, 1)
        self.assertEqual(self.team_b_stats.goals_conceded, 2)
        self.assertEqual(self.team_b_stats.matches_played, 1)

        # 2. Update score of FINISHED match (Team A wins 3-0)
        self.match1.home_score = 3
        self.match1.away_score = 0
        self.match1.save()

        self._refresh_stats()
        self.assertEqual(self.team_a_stats.points, 3) # Still 3 points for a win
        self.assertEqual(self.team_a_stats.wins, 1)
        self.assertEqual(self.team_a_stats.goals_scored, 3) # Goals updated
        self.assertEqual(self.team_a_stats.goals_conceded, 0) # Goals updated
        self.assertEqual(self.team_a_stats.matches_played, 1)

        self.assertEqual(self.team_b_stats.points, 0)
        self.assertEqual(self.team_b_stats.losses, 1)
        self.assertEqual(self.team_b_stats.goals_scored, 0)
        self.assertEqual(self.team_b_stats.goals_conceded, 3)
        self.assertEqual(self.team_b_stats.matches_played, 1)

        # 3. Change match status back to SCHEDULED
        self.match1.status = MatchStatus.SCHEDULED
        self.match1.save()

        self._assert_initial_stats() # All stats should revert to 0

        # 4. Change match to FINISHED (Draw 1-1)
        self.match1.home_score = 1
        self.match1.away_score = 1
        self.match1.status = MatchStatus.FINISHED
        self.match1.save()

        self._refresh_stats()
        self.assertEqual(self.team_a_stats.points, 1)
        self.assertEqual(self.team_a_stats.draws, 1)
        self.assertEqual(self.team_a_stats.goals_scored, 1)
        self.assertEqual(self.team_a_stats.goals_conceded, 1)
        self.assertEqual(self.team_a_stats.matches_played, 1)

        self.assertEqual(self.team_b_stats.points, 1)
        self.assertEqual(self.team_b_stats.draws, 1)
        self.assertEqual(self.team_b_stats.goals_scored, 1)
        self.assertEqual(self.team_b_stats.goals_conceded, 1)
        self.assertEqual(self.team_b_stats.matches_played, 1)

        # 5. Delete the FINISHED match
        self.match1.delete()

        self._assert_initial_stats() # All stats should revert to 0

    def test_match_not_affecting_stats_when_not_finished(self):
        # Create a match that is not finished
        match2 = Match.objects.create(
            season=self.league,
            home_team=self.team_a,
            away_team=self.team_c,
            home_score=5,
            away_score=0,
            date=timezone.now(),
            status=MatchStatus.LIVE # Live match
        )
        self._assert_initial_stats() # Stats should still be 0

        match2.status = MatchStatus.SCHEDULED # Change status, still no effect
        match2.save()
        self._assert_initial_stats() # Stats should still be 0

        match2.delete() # Delete, still no effect
        self._assert_initial_stats() # Stats should still be 0


class PlayerStatsAggregationTests(TestCase):
    """Tests the automated aggregation of player stats into PlayerSeasonParticipation."""

    def setUp(self):
        self.league = League.objects.create(year=2025, session='S', is_active=True)
        self.team1 = Team.objects.create(name="Team Alpha")
        self.player1 = Player.objects.create(first_name="Player", last_name="One", position="GK")
        self.player2 = Player.objects.create(first_name="Player", last_name="Two", position="FW")

        self.player1_psp = PlayerSeasonParticipation.objects.create(
            player=self.player1, team=self.team1, league=self.league, is_active=True,
            goals=0, assists=0, yellow_cards=0, red_cards=0
        )
        self.player2_psp = PlayerSeasonParticipation.objects.create(
            player=self.player2, team=self.team1, league=self.league, is_active=True,
            goals=0, assists=0, yellow_cards=0, red_cards=0
        )

        self.match1 = Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=Team.objects.create(name="Opponent Team"),
            home_score=0, away_score=0,
            date=timezone.now(),
            status=MatchStatus.FINISHED
        )
        self.match2 = Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=Team.objects.create(name="Another Opponent"),
            home_score=0, away_score=0,
            date=timezone.now() + timedelta(days=7),
            status=MatchStatus.FINISHED
        )

    def _refresh_psp_stats(self):
        self.player1_psp.refresh_from_db()
        self.player2_psp.refresh_from_db()

    def test_player_stats_update_aggregates_on_save(self):
        # Initial stats should be zero
        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 0)
        self.assertEqual(self.player1_psp.assists, 0)

        # 1. Create a PlayerStats object (Match 1)
        player_stats1 = PlayerStats.objects.create(
            match=self.match1, player=self.player1, goals=2, assists=1, yellow_cards=0, red_cards=0
        )

        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 2)
        self.assertEqual(self.player1_psp.assists, 1)

        # 2. Create another PlayerStats object for the same player in a different match (Match 2)
        player_stats2 = PlayerStats.objects.create(
            match=self.match2, player=self.player1, goals=1, assists=1, yellow_cards=1, red_cards=0
        )

        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 3)
        self.assertEqual(self.player1_psp.assists, 2)
        self.assertEqual(self.player1_psp.yellow_cards, 1)
        self.assertEqual(self.player1_psp.red_cards, 0)

        # 3. Update an existing PlayerStats object
        player_stats1.goals = 3
        player_stats1.save()

        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 4) # 3 from match1 + 1 from match2
        self.assertEqual(self.player1_psp.assists, 2) # 1 from match1 + 1 from match2

    def test_player_stats_update_aggregates_on_delete(self):
        # Create PlayerStats first
        player_stats1 = PlayerStats.objects.create(
            match=self.match1, player=self.player1, goals=2, assists=1, yellow_cards=0, red_cards=0
        )
        player_stats2 = PlayerStats.objects.create(
            match=self.match2, player=self.player1, goals=1, assists=1, yellow_cards=1, red_cards=0
        )
        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 3)
        self.assertEqual(self.player1_psp.assists, 2)

        # 1. Delete one PlayerStats object
        player_stats1.delete()

        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 1) # Only stats from player_stats2 remain
        self.assertEqual(self.player1_psp.assists, 1)
        self.assertEqual(self.player1_psp.yellow_cards, 1)

        # 2. Delete the second PlayerStats object
        player_stats2.delete()

        self._refresh_psp_stats()
        self.assertEqual(self.player1_psp.goals, 0)
        self.assertEqual(self.player1_psp.assists, 0)
        self.assertEqual(self.player1_psp.yellow_cards, 0)

    def test_top_stats_view_reflects_updated_player_season_stats(self):
        # Create multiple PlayerStats for different players
        PlayerStats.objects.create(match=self.match1, player=self.player1, goals=3, assists=1)
        PlayerStats.objects.create(match=self.match1, player=self.player2, goals=1, assists=2)
        PlayerStats.objects.create(match=self.match2, player=self.player1, goals=1, assists=1)

        self._refresh_psp_stats() # Trigger aggregation via signals

        # Player1: 4 goals, 2 assists
        # Player2: 1 goal, 2 assists

        # Mock the request for TopStatsView
        factory = RequestFactory()
        request = factory.get(reverse('top_stats', kwargs={'league_id': self.league.id}))
        
        # Create an instance of the view and call as_view()
        view = TopStatsView()
        view.setup(request, league_id=self.league.id)
        response = view.dispatch(request, league_id=self.league.id)

        self.assertEqual(response.status_code, 200)
        
        # Check context data
        players_in_context = response.context_data['players']
        self.assertEqual(len(players_in_context), 2) # Only player1 and player2

        # Ensure ordering and correct stats
        # Should be ordered by total_goals descending
        self.assertEqual(players_in_context[0].player, self.player1)
        self.assertEqual(players_in_context[0].goals, 4)
        self.assertEqual(players_in_context[0].assists, 2)

        self.assertEqual(players_in_context[1].player, self.player2)
        self.assertEqual(players_in_context[1].goals, 1)
        self.assertEqual(players_in_context[1].assists, 2)


class MatchDetailsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(email='admin@test.com', password='password', username='admin')
        self.user = User.objects.create_user(email='user@test.com', password='password', username='user')
        self.league = League.objects.create(year=2025, session='S', is_active=True)
        self.team1 = Team.objects.create(name='Team 1')
        self.team2 = Team.objects.create(name='Team 2')
        self.match = Match.objects.create(
            season=self.league,
            home_team=self.team1,
            away_team=self.team2,
            date=timezone.now(),
            status=MatchStatus.SCHEDULED,
        )
        self.player = Player.objects.create(first_name='Test', last_name='Player', position='FW')
        self.lineup = Lineup.objects.create(match=self.match, team=self.team1)
        LineupPlayer.objects.create(lineup=self.lineup, player=self.player, is_starter=True)

    def test_match_events_visible_to_all_users(self):
        # Admin adds an event
        self.client.login(username='admin', password='password')
        self.client.post(reverse('match_details', args=[self.match.id]), {
            'event_type': 'GOAL',
            'player': self.player.id,
            'commentary': 'First goal!'
        })
        self.client.logout()

        # Regular user views the page
        self.client.login(username='user', password='password')
        response = self.client.get(reverse('match_details', args=[self.match.id]))
        self.assertContains(response, 'First goal!')
        self.assertEqual(len(response.context['events']), 1)

        # Admin adds another event
        self.client.login(username='admin', password='password')
        self.client.post(reverse('match_details', args=[self.match.id]), {
            'event_type': 'YELLOW_CARD',
            'player': self.player.id,
            'commentary': 'Yellow card for diving.'
        })
        self.client.logout()

        # Regular user views the page again
        self.client.login(username='user', password='password')
        response = self.client.get(reverse('match_details', args=[self.match.id]))
        self.assertContains(response, 'First goal!')
        self.assertContains(response, 'Yellow card for diving.')
        self.assertEqual(len(response.context['events']), 2)


class PlayerProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.league1 = League.objects.create(year=2023, session='S', is_active=False)
        self.league2 = League.objects.create(year=2024, session='A', is_active=True)
        self.team1 = Team.objects.create(name='Team A')
        self.team2 = Team.objects.create(name='Team B')
        self.player = Player.objects.create(first_name='John', last_name='Doe', position='FW')

        # Player participation in league1
        self.psp1 = PlayerSeasonParticipation.objects.create(
            player=self.player,
            team=self.team1,
            league=self.league1,
            matches_played=10,
            goals=5,
            assists=3,
            yellow_cards=1,
            red_cards=0,
            is_active=True
        )

        # Player participation in league2
        self.psp2 = PlayerSeasonParticipation.objects.create(
            player=self.player,
            team=self.team2,
            league=self.league2,
            matches_played=15,
            goals=8,
            assists=5,
            yellow_cards=2,
            red_cards=1,
            is_active=True
        )

    def test_player_profile_view_context(self):
        response = self.client.get(reverse('player_profile', args=[self.player.id]))

        self.assertEqual(response.status_code, 200)
        
        # Check if player object is in context
        self.assertIn('player', response.context)
        self.assertEqual(response.context['player'], self.player)

        # Check if season_participations are in context and ordered correctly
        self.assertIn('season_participations', response.context)
        season_participations = list(response.context['season_participations'])
        self.assertEqual(len(season_participations), 2)
        self.assertEqual(season_participations[0], self.psp2) # 2024 season first
        self.assertEqual(season_participations[1], self.psp1) # 2023 season second

        # Check if total_stats are in context and aggregated correctly
        self.assertIn('total_matches', response.context)
        self.assertEqual(response.context['total_matches'], 25) # 10 + 15

        self.assertIn('total_goals', response.context)
        self.assertEqual(response.context['total_goals'], 13) # 5 + 8

        self.assertIn('total_assists', response.context)
        self.assertEqual(response.context['total_assists'], 8) # 3 + 5

        self.assertIn('total_yellow_cards', response.context)
        self.assertEqual(response.context['total_yellow_cards'], 3) # 1 + 2

        self.assertIn('total_red_cards', response.context)
        self.assertEqual(response.context['total_red_cards'], 1) # 0 + 1

        # Check if the correct template is used
        self.assertTemplateUsed(response, 'player_profile.html')