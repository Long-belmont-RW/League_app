from django.core.management.base import BaseCommand
from league.models import Match, League

class Command(BaseCommand):
    help = "Delete matches from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", 
            action="store_true", 
            help="Delete all matches in the system"
        )
        parser.add_argument(
            "--league_id", 
            type=int, 
            help="Delete matches for a specific league by ID"
        )
        parser.add_argument(
            "--latest", 
            action="store_true", 
            help="Delete matches for the latest created league"
        )

    def handle(self, *args, **options):
        delete_all = options["all"]
        league_id = options.get("league_id")
        latest = options.get("latest")

        if delete_all:
            count, _ = Match.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted ALL {count} matches."))
            return

        if league_id:
            try:
                league = League.objects.get(id=league_id)
            except League.DoesNotExist:
                self.stderr.write(self.style.ERROR("League not found."))
                return
        elif latest:
            league = League.objects.order_by("-created_at").first()
            if not league:
                self.stderr.write(self.style.ERROR("No leagues found."))
                return
        else:
            self.stderr.write(self.style.ERROR("You must specify either --all, --league_id, or --latest"))
            return

        matches = Match.objects.filter(season=league)
        count = matches.count()
        matches.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} matches for league: {league}"))
