import random
from django.core.management.base import BaseCommand
from league.models import Match, MatchStatus

class Command(BaseCommand):
    help = 'Assigns random scores to all scheduled matches and marks them as finished.'

    def handle(self, *args, **options):
        scheduled_matches = Match.objects.filter(status=MatchStatus.SCHEDULED)
        
        if not scheduled_matches.exists():
            self.stdout.write(self.style.WARNING('No scheduled matches found to assign scores to.'))
            return

        self.stdout.write(self.style.NOTICE(f'Assigning random scores to {scheduled_matches.count()} matches...'))

        for match in scheduled_matches:
            match.home_score = random.randint(0, 5)
            match.away_score = random.randint(0, 5)
            match.status = MatchStatus.FINISHED
            match.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully assigned scores and updated status for {scheduled_matches.count()} matches.'))
