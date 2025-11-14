from django.core.management.base import BaseCommand
from league.models import Lineup, LineupPlayer, PlayerStats, MatchEvent

class Command(BaseCommand):
    help = 'Deletes all simulation-related data (Lineups, PlayerStats, MatchEvents).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Deleting simulation data...'))

        lineup_player_count = LineupPlayer.objects.all().count()
        LineupPlayer.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {lineup_player_count} LineupPlayer objects.'))

        lineup_count = Lineup.objects.all().count()
        Lineup.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {lineup_count} Lineup objects.'))

        player_stats_count = PlayerStats.objects.all().count()
        PlayerStats.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {player_stats_count} PlayerStats objects.'))

        match_event_count = MatchEvent.objects.all().count()
        MatchEvent.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {match_event_count} MatchEvent objects.'))

        self.stdout.write(self.style.SUCCESS('All simulation data has been deleted.'))
