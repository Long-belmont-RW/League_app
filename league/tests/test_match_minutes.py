from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from league.models import Match, Team, League, MatchStatus

class MatchMinuteCalculationTest(TestCase):
    def setUp(self):
        self.league = League.objects.create(year=2023, session='F', is_active=True)
        self.home_team = Team.objects.create(name="Home Team")
        self.away_team = Team.objects.create(name="Away Team")

    def create_live_match(self, minutes_elapsed_raw):
        """Helper to create a live match with a specific raw elapsed time."""
        kickoff_time = timezone.now() - timedelta(minutes=minutes_elapsed_raw)
        match = Match.objects.create(
            season=self.league,
            home_team=self.home_team,
            away_team=self.away_team,
            date=kickoff_time, # Initial date, actual_kickoff_time will be set on status change
            status=MatchStatus.SCHEDULED
        )
        # Simulate going live to set actual_kickoff_time
        match.status = MatchStatus.LIVE
        match.actual_kickoff_time = kickoff_time
        match.save()
        return match

    def test_get_raw_elapsed_minutes(self):
        # Before kickoff
        match = self.create_live_match(minutes_elapsed_raw=-10) # 10 minutes in the future
        self.assertEqual(match.get_raw_elapsed_minutes(), 0)

        # During first half
        match = self.create_live_match(minutes_elapsed_raw=20)
        self.assertEqual(match.get_raw_elapsed_minutes(), 20)

        # End of first half
        match = self.create_live_match(minutes_elapsed_raw=45)
        self.assertEqual(match.get_raw_elapsed_minutes(), 45)

        # During half-time break (e.g., 50 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=50)
        self.assertEqual(match.get_raw_elapsed_minutes(), 50)

        # Start of second half (e.g., 60 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=60)
        self.assertEqual(match.get_raw_elapsed_minutes(), 60)

        # After full time (e.g., 100 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=100)
        self.assertEqual(match.get_raw_elapsed_minutes(), 100)

        # Not live match
        match.status = MatchStatus.FINISHED
        match.save()
        self.assertIsNone(match.get_raw_elapsed_minutes())


    def test_get_current_minute_with_half_time(self):
        # Before kickoff
        match = self.create_live_match(minutes_elapsed_raw=-10) # 10 minutes in the future
        self.assertEqual(match.get_current_minute(), 0)

        # During first half
        match = self.create_live_match(minutes_elapsed_raw=20)
        self.assertEqual(match.get_current_minute(), 20)

        # End of first half
        match = self.create_live_match(minutes_elapsed_raw=45)
        self.assertEqual(match.get_current_minute(), 45)

        # During half-time break (e.g., 50 minutes raw elapsed)
        # Should still show 45 as playing time
        match = self.create_live_match(minutes_elapsed_raw=50)
        self.assertEqual(match.get_current_minute(), 45)

        # Just after half-time (e.g., 60 minutes raw elapsed, 45 playing + 15 break = 60)
        # Should be 46 playing minute (60 raw - 15 break = 45, then +1 for next minute)
        match = self.create_live_match(minutes_elapsed_raw=60)
        self.assertEqual(match.get_current_minute(), 45) # 60 - 15 = 45

        # Mid second half (e.g., 70 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=70)
        self.assertEqual(match.get_current_minute(), 55) # 70 - 15 = 55

        # Full time (e.g., 90 minutes playing time, 105 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=105)
        self.assertEqual(match.get_current_minute(), 90) # 105 - 15 = 90

        # Extra time (e.g., 95 minutes playing time, 110 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=110)
        self.assertEqual(match.get_current_minute(), 90) # Capped at 90

        # Not live match
        match.status = MatchStatus.FINISHED
        match.save()
        self.assertIsNone(match.get_current_minute())

    def test_get_display_minute_with_half_time_and_extra_time(self):
        # Before kickoff
        match = self.create_live_match(minutes_elapsed_raw=-10)
        self.assertEqual(match.get_display_minute, "0'")

        # During first half
        match = self.create_live_match(minutes_elapsed_raw=20)
        self.assertEqual(match.get_display_minute, "20'")

        # End of first half
        match = self.create_live_match(minutes_elapsed_raw=44)
        self.assertEqual(match.get_display_minute, "44'")
        match = self.create_live_match(minutes_elapsed_raw=45)
        self.assertEqual(match.get_display_minute, "HT")

        # During half-time break (e.g., 50 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=50)
        self.assertEqual(match.get_display_minute, "HT")

        # Just after half-time (e.g., 60 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=59)
        self.assertEqual(match.get_display_minute, "HT")
        match = self.create_live_match(minutes_elapsed_raw=60)
        self.assertEqual(match.get_display_minute, "45'") # 60 raw - 15 HT = 45 playing

        # Mid second half (e.g., 70 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=70)
        self.assertEqual(match.get_display_minute, "55'") # 70 raw - 15 HT = 55 playing

        # Full time (e.g., 90 minutes playing time, 105 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=105)
        self.assertEqual(match.get_display_minute, "90'") # 105 raw - 15 HT = 90 playing

        # Extra time (e.g., 92 minutes playing time, 107 minutes raw elapsed)
        match = self.create_live_match(minutes_elapsed_raw=107)
        self.assertEqual(match.get_display_minute, "90 + 2'") # 107 raw - 15 HT = 92 playing

        # Not live match
        match.status = MatchStatus.FINISHED
        match.save()
        self.assertEqual(match.get_display_minute, "")
