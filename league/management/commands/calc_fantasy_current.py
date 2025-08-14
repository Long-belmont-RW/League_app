from django.core.management.base import BaseCommand

from fantasy.models import FantasyLeague
from fantasy.utils import get_current_week
from fantasy.services import FantasyScoringService


class Command(BaseCommand):
    help = "Calculate fantasy points for the current week across all fantasy leagues that have a current week."

    def handle(self, *args, **options):
        processed = 0
        for league in FantasyLeague.objects.all():
            week = get_current_week(league)
            if not week:
                continue
            service = FantasyScoringService(league)
            service.calculate_week(week)
            processed += 1
            self.stdout.write(self.style.SUCCESS(f"Processed {league.name} – GW{week.index}"))
        if processed == 0:
            self.stdout.write("No current weeks found.")

