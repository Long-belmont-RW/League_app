from django.core.management.base import BaseCommand
from django.core import management

class Command(BaseCommand):
    help = "Run a full season simulation, including generating fixtures, assigning scores, creating lineups, and generating player stats."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting full season simulation..."))

        # 1. Generate fixtures
        self.stdout.write(self.style.NOTICE("Generating fixtures..."))
        management.call_command('generate_fixtures', double=True, start_date='2025-01-01')

        # 2. Assign random scores
        self.stdout.write(self.style.NOTICE("Assigning random scores to matches..."))
        management.call_command('assign_scores')

        # 3. Generate lineups
        self.stdout.write(self.style.NOTICE("Generating lineups for all matches..."))
        management.call_command('generate_lineups')

        # 4. Generate player stats
        self.stdout.write(self.style.NOTICE("Generating player stats for all matches..."))
        management.call_command('generate_player_stats')

        self.stdout.write(self.style.SUCCESS("Full season simulation completed successfully!"))
