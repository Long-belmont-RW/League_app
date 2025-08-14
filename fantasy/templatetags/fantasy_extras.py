from django import template
from league.models import PlayerSeasonParticipation

register = template.Library()


@register.filter(name="get_item")
def get_item(d, key):
    """
    Allows accessing dictionary items with a variable key in templates.
    Returns None if the key is not found or if an exception occurs.
    """
    if not hasattr(d, 'get'):
        return None
    return d.get(key)


@register.filter(name='filter_by_position')
def filter_by_position(fantasy_players, position):
    """
    Filters a queryset or list of FantasyPlayer objects by player position.
    """
    if not fantasy_players:
        return []
    return [fp for fp in fantasy_players if fp.player.position == position]

@register.filter(name='get_player_team_name')
def get_player_team_name(player, league):
    """
    Gets the team name for a player in a specific league.
    NOTE: This can be inefficient if used in a loop.
    """
    try:
        # Assumes a player is only in one active team per league
        participation = PlayerSeasonParticipation.objects.get(player=player, league=league, is_active=True)
        return participation.team.name
    except PlayerSeasonParticipation.DoesNotExist:
        return "N/A"
    except Exception:
        return "Error"

@register.filter
def get_at_index(list, index):
    if list and 0 <= index < len(list):
        return list[index]
    return None