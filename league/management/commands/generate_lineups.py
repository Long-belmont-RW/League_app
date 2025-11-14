import random
from django.core.management.base import BaseCommand
from league.models import Match, Team, Player, Lineup, LineupPlayer, PlayerSeasonParticipation

class Command(BaseCommand):
    help = 'Generates lineups for all matches.'

    def handle(self, *args, **options):
        matches = Match.objects.all()
        if not matches.exists():
            self.stdout.write(self.style.WARNING('No matches found to generate lineups for.'))
            return

        self.stdout.write(self.style.NOTICE(f'Generating lineups for {matches.count()} matches...'))

        for match in matches:
            for team in [match.home_team, match.away_team]:
                # Skip if a lineup already exists for this team and match
                if Lineup.objects.filter(match=match, team=team).exists():
                    continue

                # Get active players for the team in the current league
                active_players = Player.objects.filter(
                    playerseasonparticipation__team=team,
                    playerseasonparticipation__league=match.season,
                    playerseasonparticipation__is_active=True
                )

                if active_players.count() < 11:
                    self.stdout.write(self.style.WARNING(f'Not enough players for {team.name} in match {match.id}. Skipping lineup generation.'))
                    continue

                lineup = Lineup.objects.create(match=match, team=team, formation='4-4-2')

                # Randomly select 11 starters
                starters = random.sample(list(active_players), 11)
                
                for i, player in enumerate(starters):
                    LineupPlayer.objects.create(lineup=lineup, player=player, is_starter=True, position=i)

                # The rest are substitutes
                substitutes = active_players.exclude(id__in=[p.id for p in starters])
                for player in substitutes:
                    LineupPlayer.objects.create(lineup=lineup, player=player, is_starter=False)

        self.stdout.write(self.style.SUCCESS('Successfully generated lineups.'))
