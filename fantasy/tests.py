from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta, datetime
from django.utils import timezone

from league.models import Team, League as RealLeague, Player, Match, PlayerStats
from .models import (
    FantasyLeague,
    FantasyTeam,
    FantasyPlayer,
    FantasyMatchWeek,
    FantasyPlayerStats,
    FantasyLeaderboard,
)
from .services import FantasyScoringService, example_scoring_rules


class FantasyCoreTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u1", email="u1@example.com", password="pass")

        self.real_league = RealLeague.objects.create(year=2025, session='F')
        self.team_a = Team.objects.create(name="Team A")
        self.team_b = Team.objects.create(name="Team B")

        self.player_fw = Player.objects.create(first_name="John", last_name="Striker", position="FW", price=10)
        self.player_mf = Player.objects.create(first_name="Mike", last_name="Mid", position="MF", price=9)

        # Minimal fantasy league
        self.fantasy_league = FantasyLeague.objects.create(
            name="Test Fantasy", scoring_rules=example_scoring_rules(), start_date=date.today(), end_date=date.today() + timedelta(days=30),
            max_team_size=15, budget_cap=100, transfer_limit=1, max_per_real_team=3,
        )
        self.week1 = FantasyMatchWeek.objects.create(
            fantasy_league=self.fantasy_league, index=1, name="Week 1", start_date=date.today(), end_date=date.today() + timedelta(days=7),
            deadline_at=date.today(),
        )

        self.fteam = FantasyTeam.objects.create(name="Team U1", user=self.user, fantasy_league=self.fantasy_league, balance=100)

    def test_team_creation_and_add_player(self):
        FantasyPlayer.objects.create(fantasy_team=self.fteam, player=self.player_fw, price_at_purchase=10, active_from=self.fantasy_league.start_date)
        self.assertEqual(self.fteam.fantasy_players.filter(active_to__isnull=True).count(), 1)

    def test_points_calculation_and_leaderboard(self):
        # Create a match and player stats
        match = Match.objects.create(season=self.real_league, home_team=self.team_a, away_team=self.team_b, date=date.today())
        PlayerStats.objects.create(match=match, player=self.player_fw, goals=1, assists=1)

        FantasyPlayer.objects.create(fantasy_team=self.fteam, player=self.player_fw, price_at_purchase=10, active_from=self.fantasy_league.start_date)

        service = FantasyScoringService(self.fantasy_league)
        self.week1.matches.add(match)
        service.calculate_week(self.week1)

        # Check player stats and leaderboard
        fps = FantasyPlayerStats.objects.filter(fantasy_match_week=self.week1).first()
        self.assertIsNotNone(fps)
        lb_overall = FantasyLeaderboard.objects.filter(fantasy_team=self.fteam, is_overall=True).first()
        self.assertIsNotNone(lb_overall)
        self.assertGreaterEqual(lb_overall.cumulative_points, 1)

    def test_transfer_limit_and_deadline(self):
        # Set week deadline to past
        self.week1.deadline_at = timezone.now() - timedelta(days=1)
        self.week1.save(update_fields=["deadline_at"])

        # Create team and try to add player via form
        from .forms import AddFantasyPlayerForm
        form = AddFantasyPlayerForm({"player_id": self.player_mf.id}, fantasy_team=self.fteam)
        self.assertFalse(form.is_valid())
        self.assertIn("Deadline passed", str(form.errors))

    def test_set_captain(self):
        # Create active fantasy player
        fp = FantasyPlayer.objects.create(
            fantasy_team=self.fteam,
            player=self.player_fw,
            price_at_purchase=10,
            active_from=self.fantasy_league.start_date,
        )
        # Ensure deadline allows change
        self.week1.deadline_at = timezone.now() + timedelta(days=1)
        self.week1.save(update_fields=["deadline_at"])
        from .forms import SetCaptainForm
        form = SetCaptainForm({"fantasy_player_id": fp.id}, fantasy_team=self.fteam)
        self.assertTrue(form.is_valid())
        form.save()
        fp.refresh_from_db()
        self.assertTrue(fp.is_captain)