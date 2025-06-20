from django.core.management.base import BaseCommand
from tqdm import tqdm
from league.models import Player  # adjust path if needed

class Command(BaseCommand):
    help = 'Deletes all players from database'

    def handle(self, *args, **options):
        players = Player.objects.all()
        count = players.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("No players found to delete."))
            return

        confirm = input(f"Are you sure you want to delete all {count} players? (Y/n): ").strip().lower()
        if confirm != 'y':
            self.stdout.write(self.style.NOTICE("Aborted."))
            return

        self.stdout.write(self.style.WARNING("Deleting players..."))

        for player in tqdm(players, desc="Deleting", unit="player"):
            player.delete()

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully deleted {count} players."))
