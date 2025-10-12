from django.db.models import Q
from django.utils import timezone

from league.models import (
    League,
    Match,
    MatchStatus,
    TeamSeasonParticipation,
    PlayerSeasonParticipation,
)
from users.models import UserProfile


def get_latest_league():
    """Return the latest active league, or fallback to the most recently created league."""
    latest = (
        League.objects.filter(is_active=True).order_by('-created_at').first()
        or League.objects.order_by('-created_at').first()
    )
    return latest


def build_live_section(latest_league):
    if not latest_league:
        return {
            'live_match': None,
            'live_match_events': [],
        }

    live_match = (
        Match.objects.filter(season=latest_league, status=MatchStatus.LIVE)
        .select_related('home_team', 'away_team')
        .order_by('-date')
        .first()
    )
    events = live_match.get_match_events() if live_match else []

    return {
        'live_match': live_match,
        'live_match_events': events,
    }


def build_matches_section(latest_league, upcoming_limit=5, recent_limit=5):
    if not latest_league:
        return {
            'matches': [],
            'upcoming_matches': [],
            'recent_results': [],
        }

    base_qs = (
        Match.objects.filter(season=latest_league)
        .select_related('home_team', 'away_team')
    )

    matches = base_qs.order_by('-date')

    upcoming = base_qs.filter(status=MatchStatus.SCHEDULED).order_by('date')[:upcoming_limit]
    recent = base_qs.filter(status=MatchStatus.FINISHED).order_by('-date')[:recent_limit]

    return {
        'matches': matches,
        'upcoming_matches': upcoming,
        'recent_results': recent,
    }


def build_leaders_section(latest_league, leaders_limit=5):
    if not latest_league:
        return {
            'standings_top': [],
            'top_team': None,
            'top_scorers': [],
            'top_assists': [],
            'top_clean_sheets': [],
            'top_goal_scorer': None,
            'top_assist_provider': None,
            'top_clean_sheet': None,
            'top_player': None,
        }

    standings = (
        TeamSeasonParticipation.objects.filter(league=latest_league)
        .select_related('team')
        .order_by('-points', '-goals_scored', 'goals_conceded')[:leaders_limit]
    )

    psp_base = (
        PlayerSeasonParticipation.objects.filter(league=latest_league)
        .select_related('player', 'team')
    )

    top_scorers = psp_base.order_by('-goals', '-assists')[:leaders_limit]
    top_assists = psp_base.order_by('-assists', '-goals')[:leaders_limit]
    top_clean_sheets = psp_base.filter(player__position='GK').order_by('-clean_sheets')[:leaders_limit]

    context = {
        'standings_top': standings,
        'top_team': standings[0] if standings else None,
        'top_scorers': top_scorers,
        'top_assists': top_assists,
        'top_clean_sheets': top_clean_sheets,
        'top_goal_scorer': psp_base.order_by('-goals', '-assists').first(),
        'top_assist_provider': psp_base.order_by('-assists', '-goals').first(),
        'top_clean_sheet': top_clean_sheets[0] if top_clean_sheets else None,
        'top_player': psp_base.order_by('-goals', '-assists').first(),
    }
    return context


def build_personal_section(user, latest_league, favorite_limit=None):
    profile = UserProfile.objects.filter(user=user).select_related('user').first()
    if not profile:
        return {
            'fan_profile': None,
            'favorite_teams': [],
            'favorite_team_cards': [],
        }

    fav_qs = profile.favorite_teams.all().order_by('name')
    if favorite_limit:
        fav_qs = fav_qs[:favorite_limit]

    # For each favorite team, compute their next scheduled match in the latest league
    cards = []
    if latest_league:
        for team in fav_qs:
            next_match = (
                Match.objects.filter(
                    Q(home_team=team) | Q(away_team=team),
                    season=latest_league,
                    status=MatchStatus.SCHEDULED,
                )
                .select_related('home_team', 'away_team')
                .order_by('date')
                .first()
            )
            cards.append({'team': team, 'next_match': next_match})

    return {
        'fan_profile': profile,
        'favorite_teams': fav_qs,
        'favorite_team_cards': cards,
    }


def build_notifications(live_match=None, favorite_team_cards=None):
    notes = []
    if live_match:
        notes.append(
            f"Live now: {live_match.home_team} vs {live_match.away_team} • {live_match.get_display_minute}"
        )
    for card in (favorite_team_cards or []):
        team = card.get('team')
        nm = card.get('next_match')
        if nm:
            notes.append(
                f"Upcoming: {team.name} vs {nm.away_team.name if nm.home_team == team else nm.home_team.name} at {nm.date.strftime('%b %d, %I:%M %p')}"
            )
    return notes


def build_fan_dashboard_context(user):
    latest_league = get_latest_league()

    personal = build_personal_section(user, latest_league)
    live = build_live_section(latest_league)
    matches = build_matches_section(latest_league)
    leaders = build_leaders_section(latest_league)

    # Teams in the latest league (for the sidebar/cards)
    teams_in_league = TeamSeasonParticipation.objects.filter(league=latest_league).select_related('team') if latest_league else []

    notifications = build_notifications(
        live_match=live.get('live_match'),
        favorite_team_cards=personal.get('favorite_team_cards'),
    )

    # Merge all sections and keep backward-compatible keys used by existing template/view
    context = {
        'latest_league': latest_league,
        'teams': teams_in_league,
        # Personal
        **personal,
        # Live
        **live,
        # Matches
        **matches,
        # Leaders
        **leaders,
        # Notifications
        'notifications': notifications,
    }

    return context
