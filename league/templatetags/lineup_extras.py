# league/templatetags/lineup_extras.py
from django import template
import json

register = template.Library()

@register.filter(name='yojson')
def yojson(value):
    """
    Converts Python boolean to JavaScript boolean string.
    """
    if value is True:
        return 'true'
    elif value is False:
        return 'false'
    return 'null'



@register.filter(name='safe')
def safe_json(value):
    """
    Safely converts Python data structures to JSON for use in templates.
    Usage: {{ starters|safe }}
    """
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return '[]'