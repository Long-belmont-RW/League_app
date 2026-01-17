
import os
import django
import dotenv
from django.db import transaction
from django.core.exceptions import ValidationError

dotenv.load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "league_app.settings.local")
django.setup()

from fantasy.forms import AddFantasyPlayerForm
from fantasy.models import FantasyTeam
from league.models import Player, PlayerSeasonParticipation

# Wrap in transaction to rollback changes
try:
    with transaction.atomic():
        # Find the team (assuming it's full of Team A players)
        team = FantasyTeam.objects.first()
        if not team:
            print("No fantasy teams found.")
            raise Exception("Rollback")
            
        print(f"Using Team: {team.name} (User: {team.user.username})")

        # Pick a player to remove
        player_to_remove = team.fantasy_players.filter(active_to__isnull=True).first()
        if not player_to_remove:
            print("Team is empty, cannot reproduce.")
        else:
            print(f"Temporarily removing player: {player_to_remove.player.nickname}")
            player_to_remove.delete() # Or set active_to
            
            # Now we have 14 players.
            # Identify the real team of the removed player
            psp = PlayerSeasonParticipation.objects.filter(player=player_to_remove.player, is_active=True).first()
            if psp:
                real_team = psp.team
                print(f"Player belonged to: {real_team.name}")
                
                # Check count of players from this team explicitly
                count = team.fantasy_players.filter(
                    active_to__isnull=True, 
                    player__playerseasonparticipation__team_id=real_team.id,
                    player__playerseasonparticipation__is_active=True
                ).count()
                print(f"Current count from {real_team.name}: {count}")
                
                # Check League Limit
                print(f"League Limit: {team.fantasy_league.max_per_real_team}")
                
                # Try to add the SAME player back
                print(f"Attempting to add back player: {player_to_remove.player.nickname}")
                form = AddFantasyPlayerForm(data={'player_id': player_to_remove.player.id}, fantasy_team=team)
                
                if not form.is_valid():
                    print("Form Errors:")
                    print(form.errors)
                    if "Exceeded allowed number of players from this real team" in str(form.errors):
                         print("SUCCESS: Reproduced the error!")
                else:
                    print("Form valid (Unexpected - should have hit limit)")
            else:
                print("Player has no active participation.")

        # Always raise exception to rollback
        raise Exception("Rollback")
except Exception as e:
    if str(e) != "Rollback":
        raise e
    print("\nTransaction rolled back. No changes persisted.")
