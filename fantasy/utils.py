from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.utils import timezone

from .models import FantasyLeague, FantasyMatchWeek


def get_current_week(league: FantasyLeague) -> Optional[FantasyMatchWeek]:
    now = timezone.now()
    today = now.date()
    return (
        league.match_weeks.filter(start_date__lte=today, end_date__gte=today)
        .order_by("index")
        .first()
    )


def is_before_deadline(week: FantasyMatchWeek) -> bool:
    if not week or not week.deadline_at:
        return True
    now = timezone.now()
    return now <= week.deadline_at


