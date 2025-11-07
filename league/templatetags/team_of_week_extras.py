from django import template
from itertools import groupby
from operator import itemgetter

register = template.Library()

@register.filter(name='group_by')
def group_by(queryset, key):
    return [{'grouper': k, 'list': list(v)} for k, v in groupby(queryset, key=lambda x: getattr(x, key))]
