from django.core.management.base import BaseCommand, CommandError

from fantasy.models import FantasyLeague, FantasyMatchWeek
from fantasy.services import FantasyScoringService


class Command(BaseCommand):
    help = "Calculate fantasy points and leaderboard for a given FantasyLeague and MatchWeek"

    def add_arguments(self, parser):
        parser.add_argument("league_id", type=int, help="ID of the FantasyLeague")
        parser.add_argument("week_index", type=int, help="MatchWeek index (1-based)")

    def handle(self, *args, **options):
        league_id = options["league_id"]
        week_index = options["week_index"]
        try:
            league = FantasyLeague.objects.get(id=league_id)
        except FantasyLeague.DoesNotExist:
            raise CommandError(f"FantasyLeague {league_id} not found")

        try:
            week = FantasyMatchWeek.objects.get(fantasy_league=league, index=week_index)
        except FantasyMatchWeek.DoesNotExist:
            raise CommandError(f"Week index {week_index} not found for league {league.name}")

        service = FantasyScoringService(league)
        service.calculate_week(week)
        self.stdout.write(self.style.SUCCESS(f"Calculated fantasy results for {league.name} – GW{week.index}"))


