# league/templatetags/league_extras.py
from django import template

register = template.Library()

@register.filter(name='parse_formation')
def parse_formation(formation_str):
    """
    Parses a formation string like '4-4-2' into a list of lists for looping.
    Returns [[1, 2, 3, 4], [1, 2, 3, 4], [1, 2]] for '4-4-2'.
    """
    if not isinstance(formation_str, str) or not '-' in formation_str:
        return [] # Return empty list for invalid input
    try:
        parts = [int(p) for p in formation_str.split('-')]
        # We only care about defenders, midfielders, and forwards for the pitch grid rows
        rows = parts[:3]
        return [range(count) for count in rows]
    except (ValueError, TypeError):
        return [] # Return empty on parsing error

