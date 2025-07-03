from django.core.management.base import BaseCommand, CommandError
from league.models import Team, League, TeamSeasonParticipation

class Command(BaseCommand):
    help = 'Automatically register all teams in the most recent league season.'

    def handle(self, *args, **options):
        # Get the most recent league (by year, then by id as tiebreaker)
        league = League.objects.order_by('-year', '-id').first()
        if not league:
            raise CommandError('No leagues found.')
        teams = Team.objects.all()
        if not teams.exists():
            self.stdout.write(self.style.WARNING('No teams found to register.'))
            return
        registered = 0
        for team in teams:
            participation, created = TeamSeasonParticipation.objects.get_or_create(
                team=team, league=league
            )
            if created:
                registered += 1
                self.stdout.write(self.style.SUCCESS(f'Registered team {team} in league {league}'))
            else:
                self.stdout.write(self.style.WARNING(f'Team {team} is already registered in league {league}'))
        self.stdout.write(self.style.SUCCESS(f'Finished. {registered} teams registered in league {league}.'))
