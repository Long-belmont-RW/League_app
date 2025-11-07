from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from league.models import Match, League


def push_user_notification(user_id: int, payload: dict) -> None:
    """Push a realtime notification to a specific user group."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {"type": "notify", "data": payload},
    )

def get_latest_league():
    """Return the most recently created league."""
    return League.objects.order_by('-created_at').first()


def get_team_matches(team=None, season=None):
    """Return matches for a given team (or all matches if team=None) in a season."""
    if not season:
        season = get_latest_league()
    if not season:
        return Match.objects.none()

    matches = Match.objects.filter(season=season)
    if team:
        matches = matches.filter(Q(home_team=team) | Q(away_team=team))
    return matches


#Helper function to calculate season progress
def get_season_progress():
    matches = get_team_matches()
    total = matches.count()
    finished = matches.filter(status="FIN").count()
    return (finished / total) * 100 if total else 0

def get_team_season_progress(team):
    """Calculate a team's current season progress as a percentage."""
    matches = get_team_matches(team)
    total = matches.count()
    finished = matches.filter(status="FIN").count()
    
    return (round(finished / total)) * 100 if total else 0

def get_matches_completed():
    matches = get_team_matches()
    total = matches.count()
    finished = matches.filter(status="FIN").count()

    return f'{finished} / {total}'

def get_win_ratio(team):
    """Calculate a team's win ratio as a percentage."""
    matches = get_team_matches(team)
    total = matches.count()
    if total == 0:
        return 0

    finished_matches = matches.filter(status="FIN")
    won_matches = sum(1 for match in finished_matches if match.get_winner() == team)

    return (won_matches / total) * 100