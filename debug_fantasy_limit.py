
import os
import django
import dotenv
from django.db.models import Count

# Load environment using dotenv (same as manage.py)
dotenv.load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "league_app.settings.local")
django.setup()

from fantasy.models import FantasyTeam, FantasyLeague
from django.contrib.auth import get_user_model

User = get_user_model()

print("--- Debugging Fantasy Player Limit ---")

teams = FantasyTeam.objects.all()
if not teams.exists():
    print("No fantasy teams found.")
else:
    for team in teams:
        print(f"\nChecking Team: {team.name} (User: {team.user.username})")
        league = team.fantasy_league
        print(f"League: {league.name}")
        print(f"  Max Team Size: {league.max_team_size}")
        print(f"  Max Per Real Team: {league.max_per_real_team}")
        
        # Check current players
        players = team.fantasy_players.filter(active_to__isnull=True)
        print(f"  Current Active Players: {players.count()}")
        
        # Group by real team
        real_team_counts = {}
        for fp in players:
             # Logic from form
            from league.models import PlayerSeasonParticipation
            current_season_participation = PlayerSeasonParticipation.objects.filter(player=fp.player, is_active=True).first()
            if not current_season_participation:
                team_name = "Unknown (No active participation)"
            else:
                team_name = current_season_participation.team.name if current_season_participation.team else "Unknown Team"
            
            if team_name not in real_team_counts:
                real_team_counts[team_name] = 0
            real_team_counts[team_name] += 1
            
            # print(f"    - {fp.player.nickname} ({team_name})")

        print("  Composition by Real Team:")
        for team_name, count in real_team_counts.items():
            limit = league.max_per_real_team
            status = "OK" if count < limit else ("AT LIMIT" if count == limit else "EXCEEDED")
            print(f"    - {team_name}: {count}/{limit} [{status}]")

print("\n--- Data Integrity Check ---")
from league.models import PlayerSeasonParticipation
unique_teams = PlayerSeasonParticipation.objects.filter(is_active=True).values('team__name').distinct()
print(f"Distinct Active Teams in Season Participation: {unique_teams.count()}")
for t in unique_teams:
    print(f"  - {t['team__name']}")

