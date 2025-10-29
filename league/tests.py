from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from datetime import datetime, timedelta, time
from unittest.mock import patch
from django.urls import reverse
import json

import pytest, pytz
from freezegun import freeze_time

from league.models import (Team, League, Match, MatchStatus, 
        TeamSeasonParticipation, Coach, Player, 
        Lineup, CoachSeasonParticipation, PlayerSeasonParticipation, MatchEvent, LineupPlayer)
from users.models import UserProfile, Notification
from league.services import update_league_table
from .forms import MatchEventForm, LineupFormSet


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


class MatchDetailsViewTests(TestCase):
    def setUp(self):
        # Set up a client
        self.client = Client()
        
        # Create a league and teams
        self.league = League.objects.create(year=2025, session="S", is_active=True)
        self.home_team = Team.objects.create(name="Home Lions")
        self.away_team = Team.objects.create(name="Away Tigers")

        # Create players
        self.home_player = Player.objects.create(first_name="Home", last_name="Player")
        self.away_player = Player.objects.create(first_name="Away", last_name="Player")
        self.other_player = Player.objects.create(first_name="Other", last_name="Player")

        # Create a match
        self.match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=timezone.now() + timedelta(hours=1),
            status=MatchStatus.SCHEDULED
        )

        # Create lineups
        self.home_lineup = Lineup.objects.create(match=self.match, team=self.home_team)
        LineupPlayer.objects.create(lineup=self.home_lineup, player=self.home_player, is_starter=True)
        
        self.away_lineup = Lineup.objects.create(match=self.match, team=self.away_team)
        LineupPlayer.objects.create(lineup=self.away_lineup, player=self.away_player, is_starter=True)

        # URL for the match details view
        self.details_url = reverse('match_details', args=[self.match.id])

    def test_match_details_view_loads_successfully(self):
        """Tests that the match details page loads with a 200 status code."""
        response = self.client.get(self.details_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'match_details.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], MatchEventForm)

    def test_add_event_when_match_not_live(self):
        """Tests adding an event to a match that is not live sets the minute to 0."""
        self.assertEqual(self.match.status, MatchStatus.SCHEDULED)
        
        post_data = {
            'player': self.home_player.id,
            'event_type': 'GOAL',
            'commentary': 'Early goal!'
        }
        response = self.client.post(self.details_url, data=post_data)

        # Check redirect and event creation
        self.assertEqual(response.status_code, 302) # Should redirect after successful post
        self.assertTrue(MatchEvent.objects.filter(match=self.match, player=self.home_player).exists())
        
        # Check that the minute is 0
        event = MatchEvent.objects.get(match=self.match, player=self.home_player)
        self.assertEqual(event.minute, 0)

    @freeze_time("2025-08-15 15:30:00")
    def test_add_event_when_match_is_live(self):
        """Tests adding an event to a live match captures the correct minute."""
        # Set the match to live, starting 15 minutes ago
        self.match.status = MatchStatus.LIVE
        self.match.actual_kickoff_time = timezone.now() - timedelta(minutes=15)
        self.match.save()

        post_data = {
            'player': self.away_player.id,
            'event_type': 'YELLOW_CARD',
            'commentary': 'A tactical foul.'
        }
        response = self.client.post(self.details_url, data=post_data)

        # Check redirect and event creation
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MatchEvent.objects.filter(match=self.match, player=self.away_player).exists())

        # Check that the minute is correctly captured
        event = MatchEvent.objects.get(match=self.match, player=self.away_player)
        self.assertEqual(event.minute, 15)

    def test_event_form_only_shows_lineup_players(self):
        """Tests that the player dropdown in the form is correctly filtered."""
        response = self.client.get(self.details_url)
        form = response.context['form']
        
        # Get the queryset of the player field
        form_player_queryset = form.fields['player'].queryset
        
        # Check that the players in the form are the ones in the lineup
        self.assertIn(self.home_player, form_player_queryset)
        self.assertIn(self.away_player, form_player_queryset)
        
        # Check that a player not in the lineup is NOT in the form choices
        self.assertNotIn(self.other_player, form_player_queryset)
        self.assertEqual(len(form_player_queryset), 2)
class ManageLineupJSONViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='coach', password='password', role='coach', email='coach@test.com')
        self.user.refresh_from_db()
        self.coach = self.user.userprofile.coach

        self.league = League.objects.create(year=2025, session='S', is_active=True)
        self.home_team = Team.objects.create(name='Home Team')
        self.away_team = Team.objects.create(name='Away Team')

        self.home_players = []
        for i in range(15):
            p = Player.objects.create(first_name=f'HomePlayer', last_name=str(i))
            PlayerSeasonParticipation.objects.create(player=p, team=self.home_team, league=self.league, is_active=True)
            self.home_players.append(p)

        self.match = Match.objects.create(season=self.league, home_team=self.home_team, away_team=self.away_team, date=timezone.now())
        CoachSeasonParticipation.objects.create(coach=self.coach, team=self.home_team, league=self.league)

        self.client.login(username='coach@test.com', password='password')
        self.url = reverse('manage_lineup', args=[self.match.id])

    def test_save_and_reload_lineup(self):
        """
        Tests that a lineup saved via JSON POST is correctly retrieved on a subsequent GET request.
        """
        starters = self.home_players[:11]
        substitutes = self.home_players[11:15]
        
        post_data = {
            'team_id': self.home_team.id,
            'starters': [p.id for p in starters],
            'substitutes': [p.id for p in substitutes],
            'formation': '4-3-3',
        }

        # POST the lineup
        response = self.client.post(self.url, data=json.dumps(post_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'success')

        # Verify the database state
        self.assertTrue(Lineup.objects.filter(match=self.match, team=self.home_team).exists())
        lineup = Lineup.objects.get(match=self.match, team=self.home_team)
        self.assertEqual(lineup.formation, '4-3-3')
        self.assertEqual(lineup.lineupplayer_set.filter(is_starter=True).count(), 11)
        self.assertEqual(lineup.lineupplayer_set.filter(is_starter=False).count(), 4)

        # GET the lineup manager again
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, 200)

        # Check the context data
        home_team_context = get_response.context['home_team_context']
        js_data = home_team_context['js_data']
        
        self.assertEqual(js_data['formation'], '4-3-3')
        self.assertEqual(len(js_data['starters']), 11)
        self.assertEqual(len(js_data['substitutes']), 4)
        
        # Check that the correct players are in the lists
        starter_ids_from_context = {p['id'] for p in js_data['starters']}
        self.assertEqual(starter_ids_from_context, {p.id for p in starters})