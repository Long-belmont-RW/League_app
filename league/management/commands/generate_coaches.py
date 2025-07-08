import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from faker import Faker
from tqdm import tqdm

from league.models import Team, Player, League, CoachSeasonParticipation, CoachRoles, Coach

fake = Faker()


class Command(BaseCommand):
    help = 'Generates two coaches per team and registers them in a league'

    def handle(self, *args, **options):
        #Get the current Active League

        league = League.objects.filter(is_active=True).order_by('-year').first()

        if not league:
            self.stdout.write(self.style.ERROR("No active leagues found. Please create one first"))
            return
        
        teams = Team.objects.all()
        total_coaches_registerd = 0
        total_coaches_created = 0

        #check if teams exists
        if teams.count() == 0:
            self.stdout(self.style.WARNING("No teams found. Please create teams first"))
            return
        

        for team in tqdm(teams, desc="Generating Coaches for teams", unit="team"):

            #Generate Random Birth Dates
            birth_date = date.today() - timedelta(days=random.randint(18*365, 30*365))

            Assistant_coach = Coach.objects.create(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                bio=fake.sentence,
                birth=birth_date,
                role=CoachRoles.ASSISTANT,
                is_active=True
            )

            Head_coach = Coach.objects.create(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                bio=fake.sentence,
                birth=birth_date,
                role=CoachRoles.HEAD,
                is_active=True
            )


            CoachSeasonParticipation.objects.create(
                coach=Head_coach,
                team = team,
                league=league,
               
            )   

            total_coaches_created +=2
            total_coaches_registerd += 2

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Created {total_coaches_created} Coaches and Registered {total_coaches_registerd} s."
        ))


    
