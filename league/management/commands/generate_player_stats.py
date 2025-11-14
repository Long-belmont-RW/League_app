import random
from django.core.management.base import BaseCommand
from league.models import Match, PlayerStats, MatchEvent, Lineup, MatchStatus

class Command(BaseCommand):
    help = 'Generates random player stats for finished matches.'

    def handle(self, *args, **options):
        finished_matches = Match.objects.filter(status=MatchStatus.FINISHED)

        if not finished_matches.exists():
            self.stdout.write(self.style.WARNING('No finished matches found to generate stats for.'))
            return

        self.stdout.write(self.style.NOTICE(f'Generating player stats for {finished_matches.count()} matches...'))

        for match in finished_matches:
            # Skip if stats already exist for this match
            if PlayerStats.objects.filter(match=match).exists():
                continue

            self._generate_stats_for_match(match)

        self.stdout.write(self.style.SUCCESS('Successfully generated player stats.'))

    def _generate_stats_for_match(self, match):
        try:
            home_lineup = Lineup.objects.get(match=match, team=match.home_team)
            away_lineup = Lineup.objects.get(match=match, team=match.away_team)
        except Lineup.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'Lineup not found for match {match.id}. Skipping stats generation.'))
            return

        home_players = list(home_lineup.players.all())
        away_players = list(away_lineup.players.all())

        if not home_players or not away_players:
            self.stdout.write(self.style.WARNING(f'No players in lineup for match {match.id}. Skipping stats generation.'))
            return

        # Generate goals
        self._generate_goals(match, match.home_score, home_players)
        self._generate_goals(match, match.away_score, away_players)

        # Generate other stats like assists and cards
        self._generate_other_events(match, home_players + away_players)

    def _generate_goals(self, match, score, players):
        for _ in range(score):
            goal_scorer = random.choice(players)
            minute = random.randint(1, 90)

            # Create a MatchEvent for the goal
            MatchEvent.objects.create(
                match=match,
                player=goal_scorer,
                event_type='GOAL',
                minute=minute,
                commentary=f'{goal_scorer} scored a goal!'
            )

            # Update PlayerStats for the goal scorer
            stats, created = PlayerStats.objects.get_or_create(match=match, player=goal_scorer)
            stats.goals += 1
            stats.save()

            # Potentially create an assist
            if random.random() > 0.5: # 50% chance of an assist
                # Exclude the goal scorer from being the assister
                possible_assisters = [p for p in players if p != goal_scorer]
                if possible_assisters:
                    assister = random.choice(possible_assisters)
                    MatchEvent.objects.create(
                        match=match,
                        player=assister,
                        event_type='ASSIST',
                        minute=minute,
                        commentary=f'{assister} assisted the goal.'
                    )
                    stats, created = PlayerStats.objects.get_or_create(match=match, player=assister)
                    stats.assists += 1
                    stats.save()

    def _generate_other_events(self, match, players):
        # Generate yellow cards
        for _ in range(random.randint(0, 4)):
            player = random.choice(players)
            minute = random.randint(1, 90)
            MatchEvent.objects.create(
                match=match,
                player=player,
                event_type='YELLOW_CARD',
                minute=minute
            )
            stats, created = PlayerStats.objects.get_or_create(match=match, player=player)
            stats.yellow_cards += 1
            stats.save()
