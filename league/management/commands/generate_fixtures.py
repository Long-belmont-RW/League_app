from django.core.management.base import BaseCommand
from league.models import League, Match, TeamSeasonParticipation
from django.utils import timezone
from itertools import combinations
from datetime import timedelta
import random

class Command(BaseCommand):
    help = "Generate round-robin match fixtures for the latest league"

    def add_arguments(self, parser):
        parser.add_argument("--double", action="store_true", help="Generate home & away matches")
        parser.add_argument("--start_date", type=str, help="Optional start date: YYYY-MM-DD", default=None)
        parser.add_argument("--interval", type=int, help="Days between matches", default=7)

    def handle(self, *args, **options):
        double_round = options["double"]
        start_date_str = options["start_date"]
        interval_days = options["interval"]

        league = League.objects.order_by("-created_at").first()
        if not league:
            self.stderr.write(self.style.ERROR("No leagues found."))
            return

        active_teams = list(TeamSeasonParticipation.objects.filter(
            league=league,
        ).values_list("team", flat=True))

        if len(active_teams) < 2:
            self.stderr.write(self.style.ERROR("At least 2 active teams required to generate fixtures."))
            return

        self.stdout.write(self.style.NOTICE(f"Generating fixtures for latest league: {league}"))

        fixtures = list(combinations(active_teams, 2))

        if double_round:
            fixtures += [(b, a) for a, b in fixtures]

        random.shuffle(fixtures)

        match_day = 1
        start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        created_matches = 0

        for i, (home_id, away_id) in enumerate(fixtures):
            if home_id == away_id:
                continue

            match_date = start_date + timedelta(days=interval_days * (match_day - 1)) if start_date else timezone.now()

            match = Match(
                season=league,
                home_team_id=home_id,
                away_team_id=away_id,
                date=match_date,
                match_day=match_day
            )

            try:
                match.full_clean()  # Run model validations
                match.save()
                created_matches += 1
                match_day += 1
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Skipped match: {e}"))

        self.stdout.write(self.style.SUCCESS(f"{created_matches} matches successfully created for league {league}."))
        if created_matches == 0:
            self.stderr.write(self.style.ERROR("No matches were created. Check for validation errors."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Fixtures generated successfully with {len(fixtures)} total matches."))