import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from faker import Faker
from tqdm import tqdm

from league.models import Team, Player, League, PlayerSeasonParticipation

fake = Faker()

POSITIONS = ['GK', 'DF', 'MF', 'FW']

class Command(BaseCommand):
    help = 'Generate 11 random players per team and register them in the most recent season'

    def handle(self, *args, **options):
        #Get the current Active League

        league = League.objects.filter(is_active=True).order_by('-year').first()

        if not league:
            self.stdout.write(self.style.ERROR("No active leagues found. Please create one first"))
            return
        
        teams = Team.objects.all()
        total_players_created = 0
        total_players_registered = 0

        #check if teams exists
        if teams.count() == 0:
            self.stdout(self.style.WARNING("No teams found. Please create teams first"))
            return
        
        
        
        for team in tqdm(teams, desc="Generating players for teams", unit="team"):     

            for i in tqdm(range(11), desc=f"{team.name}", leave=False):
                #Generate random birth dates between 18 and 30 years ago

                birth_date = date.today() - timedelta(days=random.randint(18*365, 30*365))

                player = Player.objects.create(
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    bio=fake.sentence,
                    birth=birth_date,
                    position=random.choice(POSITIONS)

                )

                PlayerSeasonParticipation.objects.create(
                    player=player,
                    team=team,
                    league=league,
                    is_active=True,
                )

                total_players_created += 1
                total_players_registered += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Created {total_players_created} players and {total_players_registered} season participations."
        ))