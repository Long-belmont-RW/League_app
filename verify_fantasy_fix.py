
import os
import django
from django.conf import settings
from django.db import connection, reset_queries
import time
import dotenv

dotenv.load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'league_app.settings.local')
django.setup()
settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from django.contrib.auth import get_user_model
from fantasy.models import FantasyLeague, FantasyTeam, FantasyPlayer
from league.models import Player, Team, League, PlayerSeasonParticipation
from django.test import RequestFactory
from fantasy.views import my_fantasy_team
from django.urls import reverse

User = get_user_model()

def verify_fixes():
    print("--- Verifying Fantasy App Fixes ---")

    # 1. Setup Test Data
    # Create User
    user, _ = User.objects.get_or_create(username='testuser_fantasy', email='test@example.com')
    
    # Create League
    league, _ = League.objects.get_or_create(year=2025, session='S', is_active=True)
    
    # Create Real Team
    real_team, _ = Team.objects.get_or_create(name="Real Team A")
    
    # Create Players (15 players: 2 GK, 5 DF, 5 MF, 3 FW)
    players = []
    positions = ['GK']*2 + ['DF']*5 + ['MF']*5 + ['FW']*3
    for i, pos in enumerate(positions):
        p, _ = Player.objects.get_or_create(
            first_name=f"Player{i}", 
            last_name=f"Test{i}", 
            defaults={'position': pos, 'price': 5.0}
        )
        players.append(p)
        # Add participation
        PlayerSeasonParticipation.objects.get_or_create(
            player=p, 
            league=league, 
            team=real_team,
            defaults={'is_active': True}
        )

    # Create Fantasy League
    fl, _ = FantasyLeague.objects.get_or_create(
        name="Test Fantasy League",
        defaults={
            'start_date': "2025-01-01", 
            'end_date': "2025-12-31",
            'budget_cap': 100.0,
            'max_team_size': 15
        }
    )

    # Create Fantasy Team
    ft, created = FantasyTeam.objects.get_or_create(
        user=user, 
        fantasy_league=fl,
        defaults={'name': "My Test Team", 'balance': 100.0}
    )
    
    # Add players to fantasy team
    if created or ft.fantasy_players.count() < 15:
        ft.fantasy_players.all().delete()
        for p in players:
            FantasyPlayer.objects.create(
                fantasy_team=ft,
                player=p,
                price_at_purchase=p.price,
                active_from="2025-01-01"
            )
            
    # 2. Verify N+1 Fix
    print("\n[Test] Checking Query Count (N+1 Fix)...")
    factory = RequestFactory()
    request = factory.get(reverse('fantasy:my_team', args=[fl.id]))
    request.user = user
    
    reset_queries()
    # We use client to get the full render and query count roughly
    from django.test import Client
    client = Client()
    client.force_login(user)
    
    reset_queries()
    response = client.get(reverse('fantasy:my_team', args=[fl.id]))
    
    query_count = len(connection.queries)
    print(f"Total Queries: {query_count}")
    
    # Analyze Queries
    # If N+1 was present, we'd expect 15+ queries for participation. 
    
    if query_count < 20: # arbitrary safe threshold, assuming typical django overhead
        print("PASS: Query count is low.")
    else:
        print(f"FAIL: Query count is high ({query_count}), possible N+1.")

    # 3. Verify Bench Logic
    print("\n[Test] Checking Bench Logic (Context)...")
    
    if response.status_code == 200:
        context = response.context
        subs = context.get('substitute_players')
        
        # Guard against None
        if subs is None:
            print("FAIL: 'substitute_players' not in context!")
            return

        print(f"Total Active: {len(context.get('active_players'))}")
        print(f"Substitutes in Context: {len(subs)}")
        
        # We have 15 players:
        # GKs: 2 -> 1 Starter, 1 Sub
        # DFs: 5 -> 4 Starter, 1 Sub
        # MFs: 5 -> 3 Starter, 2 Subs
        # FWs: 3 -> 3 Starter, 0 Subs
        # Total Subs Expected: 1 + 1 + 2 + 0 = 4
        
        if len(subs) == 4:
             print("PASS: Correct number of substitutes calculated.")
        else:
             print(f"FAIL: Expected 4 substitutes, got {len(subs)}.")
             
        # Check Squad Size logic
        content = response.content.decode('utf-8')
        if "Squad: 15 / 15" in content or "15 / 15" in content:
             print("PASS: Squad size counter found in HTML.")
        else:
             print("FAIL: Squad size counter not found in HTML.")
             
    else:
        print(f"FAIL: Could not load page. Status: {response.status_code}")
        print(f"Content: {response.content.decode('utf-8')[:500]}")

if __name__ == "__main__":
    verify_fixes()
