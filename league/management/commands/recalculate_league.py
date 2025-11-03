from django.core.management.base import BaseCommand
from league.models import League, TeamSeasonParticipation


class Command(BaseCommand):
    help = "Recalculates all statistics for all teams in a specified league"


    def add_arguments(self, parser):
        parser.add_argument('league_year', type=str, help='The league year')

    def handle(self, *args, **options):
        league_year = options['league_year']

        try:
            league = League.objects.get(year=league_year)
        except League.DoesNotExist:
            league = League.objects.all().first()
        
        self.stdout.write(f'Recalculating stats for league: {league}....')
        
         # Get all team participations for this league
        participations = TeamSeasonParticipation.objects.filter(league=league)
        
        count = 0
        for participation in participations:
            self.stdout.write(f'Updating stats for {participation.team.name}...')
            participation.update_stats()
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f'Successfully recalculated stats for {count} teams in {league}.'))
