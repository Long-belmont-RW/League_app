from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def push_user_notification(user_id: int, payload: dict) -> None:
    """Push a realtime notification to a specific user group."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {"type": "notify", "data": payload},
    )
from league.models import Match, League





#Helper function to calculate season progress
def get_season_progress():
    """Calculate the progress of the current season as a percentage."""
    # Get all matches in the current season
    latest_league = League.objects.order_by('-created_at').first()
    matches = Match.objects.filter(season=latest_league)
    total_matches = matches.count()
    completed_matches = matches.filter(status='FIN').count()
    if total_matches == 0:
        return 0
    return (completed_matches / total_matches) * 100

