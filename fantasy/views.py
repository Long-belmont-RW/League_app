from __future__ import annotations

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import FantasyLeague, FantasyTeam, FantasyMatchWeek, FantasyLeaderboard, FantasyPlayer
from django.db import models
from .forms import (
    FantasyTeamCreateForm,
    AddFantasyPlayerForm,
    RemoveFantasyPlayerForm,
    SetCaptainForm,
    SetViceCaptainForm,
)
from league.models import Player
from .utils import get_current_week, is_before_deadline


def fantasy_league_list(request: HttpRequest) -> HttpResponse:
    leagues = FantasyLeague.objects.all().order_by("-created_at")
    return render(request, "fantasy/league_list.html", {"leagues": leagues})


def fantasy_league_detail(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    weeks = league.match_weeks.all().order_by("index")
    return render(request, "fantasy/league_detail.html", {"league": league, "weeks": weeks})


@login_required
def my_fantasy_team(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = FantasyTeam.objects.filter(user=request.user, fantasy_league=league).first()
    # Filters for available players
    q = request.GET.get("q", "").strip()
    pos = request.GET.get("position", "").strip()
    available_players_qs = Player.objects.all()
    if pos:
        available_players_qs = available_players_qs.filter(position=pos)
    if q:
        available_players_qs = available_players_qs.filter(
            models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q)
        )
    available_players = available_players_qs.order_by("last_name", "first_name")[:100]

    
    if team:
        from django.db.models import Prefetch
        from league.models import PlayerSeasonParticipation
        
        active_players = list(
            team.fantasy_players.filter(active_to__isnull=True)
            .select_related("player")
            .prefetch_related(
                Prefetch(
                    "player__playerseasonparticipation_set",
                    queryset=PlayerSeasonParticipation.objects.filter(is_active=True).select_related("team"),
                    to_attr="active_participation_list"
                )
            )
        )
    else:
        active_players = []

    # Transfers left and weekly points mapping
    transfers_left = None
    player_points_map = {}
    current_week = get_current_week(league)
    deadline_open = True
    if current_week:
        deadline_open = is_before_deadline(current_week)
    if team and current_week:
        from .models import FantasyTransfer, FantasyPlayerStats
        used = FantasyTransfer.objects.filter(
            fantasy_team=team,
            fantasy_match_week=current_week,
            action__in=[FantasyTransfer.Action.ADD, FantasyTransfer.Action.SWAP],
        ).count()
        transfers_left = max(0, league.transfer_limit - used)
        stats = FantasyPlayerStats.objects.filter(
            fantasy_match_week=current_week, fantasy_player__in=active_players
        ).values("fantasy_player_id", "points")
        player_points_map = {row["fantasy_player_id"]: row["points"] for row in stats}

    # Aggregate position counts and per-real-team counts
    position_counts = {"GK": 0, "DF": 0, "MF": 0, "FW": 0}
    # Separate starters and subs for context (though mostly used for subs logic)
    gks = []
    dfs = []
    mfs = []
    fws = []

    for fp in active_players:
        pos_code = getattr(fp.player, "position", None)
        if pos_code in position_counts:
            position_counts[pos_code] += 1
        
        if pos_code == "GK":
            gks.append(fp)
        elif pos_code == "DF":
            dfs.append(fp)
        elif pos_code == "MF":
            mfs.append(fp)
        elif pos_code == "FW":
            fws.append(fp)

    # Simple 1-4-3-3 split logic for bench calculation
    # Starters are just the first N in the list
    substitute_players = (
        gks[1:] + 
        dfs[4:] + 
        mfs[3:] + 
        fws[3:]
    )

    # Prepare pitch rows for the template
    # Format: {"label": str, "slots": [FantasyPlayer|None, ...]}
    def make_row(label, players, capacity):
        row_slots = players[:capacity]
        # Pad with None
        while len(row_slots) < capacity:
            row_slots.append(None)
        return {"label": label, "slots": row_slots}

    pitch_rows = [
        make_row("Goalkeepers", gks, 1),
        make_row("Defenders", dfs, 4),
        make_row("Midfielders", mfs, 3),
        make_row("Forwards", fws, 3),
    ]

    real_team_counts = {}
    
    # No try/except block needed as we handle data safely now
    for fp in active_players:
        # Use prefetched participation
        # We used active_participation_list from the Prefetch
        participations = getattr(fp.player, 'active_participation_list', [])
        psp = participations[0] if participations else None
        
        if psp and psp.team:
            name = psp.team.name
            real_team_counts[name] = real_team_counts.get(name, 0) + 1

    return render(
        request,
        "fantasy/my_team.html",
        {
            "league": league,
            "team": team,
            "available_players": available_players,
            "active_players": active_players,
            "transfers_left": transfers_left,
            "player_points_map": player_points_map,
            "current_week": current_week,
            "deadline_open": deadline_open,
            "filter_position": pos,
            "filter_q": q,
            "position_choices": Player._meta.get_field("position").choices,
            "position_counts": position_counts,
            "real_team_counts": real_team_counts,
            "max_per_real_team": league.max_per_real_team,
            "max_team_size": league.max_team_size,
            "substitute_players": substitute_players,
            "pitch_rows": pitch_rows,
        },
    )


def fantasy_leaderboard(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    overall_entries = (
        FantasyLeaderboard.objects.filter(fantasy_team__fantasy_league=league, is_overall=True)
        .select_related("fantasy_team")
        .order_by("rank")
    )
    latest_week = league.match_weeks.order_by("-index").first()
    weekly_entries = (
        FantasyLeaderboard.objects.filter(fantasy_team__fantasy_league=league, fantasy_match_week=latest_week)
        .select_related("fantasy_team")
        .order_by("rank")
        if latest_week
        else []
    )

    return render(
        request,
        "fantasy/leaderboard.html",
        {"league": league, "overall_entries": overall_entries, "weekly_entries": weekly_entries, "latest_week": latest_week},
    )


def fantasy_week_summary(request: HttpRequest, league_id: int, week_index: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    week = get_object_or_404(FantasyMatchWeek, fantasy_league=league, index=week_index)
    entries = (
        FantasyLeaderboard.objects.filter(fantasy_match_week=week, is_overall=False)
        .select_related("fantasy_team")
        .order_by("rank")
    )
    player_stats = week.player_stats.select_related("fantasy_player__player", "fantasy_player__fantasy_team").all()
    return render(
        request,
        "fantasy/week_summary.html",
        {"league": league, "week": week, "entries": entries, "player_stats": player_stats},
    )


@login_required
def fantasy_transfers(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = FantasyTeam.objects.filter(user=request.user, fantasy_league=league).first()
    if team is None:
        return redirect("fantasy:my_team", league_id=league.id)
    transfers = team.transfers.select_related("fantasy_match_week", "player_in", "player_out").order_by("-created_at")
    return render(request, "fantasy/transfers.html", {"league": league, "team": team, "transfers": transfers})


@login_required
@require_POST
def create_fantasy_team(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = FantasyTeam.objects.filter(user=request.user, fantasy_league=league).first()
    if team:
        messages.warning(request, "You already have a team in this league.")
        return redirect("fantasy:my_team", league_id=league.id)

    form = FantasyTeamCreateForm(request.POST)
    if form.is_valid():
        team = form.save(commit=False)
        team.user = request.user
        team.fantasy_league = league
        team.balance = league.budget_cap
        team.save()
        messages.success(request, "Fantasy team created")
    else:
        messages.error(request, "Error creating team")
    
    return redirect("fantasy:my_team", league_id=league.id)


@login_required
@require_POST
def add_player_to_team(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = get_object_or_404(FantasyTeam, user=request.user, fantasy_league=league)
    
    form = AddFantasyPlayerForm(request.POST, fantasy_team=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Player added to team")
    else:
        messages.error(request, "; ".join([str(e) for e in form.errors.values()]))
        
    return redirect("fantasy:my_team", league_id=league.id)


@login_required
@require_POST
def remove_player_from_team(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = get_object_or_404(FantasyTeam, user=request.user, fantasy_league=league)
    
    form = RemoveFantasyPlayerForm(request.POST, fantasy_team=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Player removed from team")
    else:
        messages.error(request, "; ".join([str(e) for e in form.errors.values()]))

    return redirect("fantasy:my_team", league_id=league.id)


@login_required
@require_POST
def set_captain(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = get_object_or_404(FantasyTeam, user=request.user, fantasy_league=league)
    
    form = SetCaptainForm(request.POST, fantasy_team=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Captain set")
    else:
        messages.error(request, "; ".join([str(e) for e in form.errors.values()]))

    return redirect("fantasy:my_team", league_id=league.id)


@login_required
@require_POST
def set_vice_captain(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(FantasyLeague, id=league_id)
    team = get_object_or_404(FantasyTeam, user=request.user, fantasy_league=league)
    
    form = SetViceCaptainForm(request.POST, fantasy_team=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Vice-captain set")
    else:
        messages.error(request, "; ".join([str(e) for e in form.errors.values()]))

    return redirect("fantasy:my_team", league_id=league.id)


