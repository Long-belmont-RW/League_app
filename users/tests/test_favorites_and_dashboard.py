from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from league.models import League, Team, Match, MatchStatus
from users.models import UserProfile
from users.services.fan_dashboard import build_fan_dashboard_context


User = get_user_model()


class FavoritesAndDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="fan@example.com", password="pass123", username="fan", role="fan")
        # Ensure a profile exists
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)

    def test_userprofile_can_follow_multiple_teams(self):
        t1 = Team.objects.create(name="Team One")
        t2 = Team.objects.create(name="Team Two")

        self.profile.favorite_teams.add(t1, t2)
        self.assertEqual(self.profile.favorite_teams.count(), 2)
        self.assertSetEqual(set(self.profile.favorite_teams.all()), {t1, t2})

    def test_dashboard_includes_favorite_team_cards_with_next_match(self):
        league = League.objects.create(year=2025, session="S", is_active=True)
        t1 = Team.objects.create(name="Alpha")
        t2 = Team.objects.create(name="Beta")
        self.profile.favorite_teams.add(t1, t2)

        now = timezone.now()
        m1 = Match.objects.create(season=league, home_team=t1, away_team=t2, date=now + timedelta(days=1), status=MatchStatus.SCHEDULED)
        m2 = Match.objects.create(season=league, home_team=t2, away_team=t1, date=now + timedelta(days=3), status=MatchStatus.SCHEDULED)

        ctx = build_fan_dashboard_context(self.user)
        cards = ctx.get('favorite_team_cards')
        self.assertTrue(cards)
        # ensure both teams appear
        teams_in_cards = {c['team'] for c in cards}
        self.assertSetEqual(teams_in_cards, {t1, t2})
        # ensure next match points to the earliest one
        for c in cards:
            self.assertIsNotNone(c['next_match'])
            self.assertEqual(c['next_match'].date, m1.date)

    def test_upcoming_matches_are_limited_and_ordered(self):
        league = League.objects.create(year=2025, session="S", is_active=True)
        a = Team.objects.create(name="A")
        b = Team.objects.create(name="B")

        now = timezone.now()
        # Create 6 upcoming matches
        for i in range(6):
            Match.objects.create(
                season=league,
                home_team=a,
                away_team=b,
                date=now + timedelta(days=i + 1),
                status=MatchStatus.SCHEDULED,
            )

        ctx = build_fan_dashboard_context(self.user)
        upcoming = list(ctx.get('upcoming_matches', []))
        self.assertEqual(len(upcoming), 5)  # limited to 5 by default
        # Check ascending by date
        dates = [m.date for m in upcoming]
        self.assertEqual(dates, sorted(dates))

    def test_no_league_returns_empty_structures(self):
        ctx = build_fan_dashboard_context(self.user)
        self.assertIsNone(ctx.get('latest_league'))
        self.assertEqual(list(ctx.get('upcoming_matches', [])), [])
        self.assertEqual(list(ctx.get('recent_results', [])), [])
