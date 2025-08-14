from django.core.management.base import BaseCommand

from fantasy.models import FantasyLeague
from fantasy.services import FantasyScoringService
from fantasy.utils import get_current_week


class Command(BaseCommand):
    help = "Calculate fantasy points and leaderboards for current weeks across all leagues"

    def handle(self, *args, **options):
        leagues = FantasyLeague.objects.all()
        processed = 0
        for league in leagues:
            week = get_current_week(league)
            if not week:
                continue
            service = FantasyScoringService(league)
            service.calculate_week(week)
            processed += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} league(s) current week"))


