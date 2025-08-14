from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from django.db import transaction
from django.db.models import Q, Sum

from .models import (
    FantasyLeague,
    FantasyTeam,
    FantasyPlayer,
    FantasyMatchWeek,
    FantasyPlayerStats,
    FantasyLeaderboard,
)

# Real league models
from league.models import Match, Player, PlayerStats, Lineup, PlayerSeasonParticipation


DEFAULT_SCORING_RULES: Dict = {
    "goal": {"GK": 6, "DF": 6, "MF": 5, "FW": 4},
    "assist": 3,
    "clean_sheet": {"GK": 4, "DF": 4, "MF": 1, "FW": 0},
    "yellow_card": -1,
    "red_card": -3,
}


@dataclass
class PlayerWeekPoints:
    total_points: int
    breakdown: Dict


class FantasyScoringService:
    """Service responsible for calculating fantasy points and updating leaderboards.

    The service reads configurable scoring rules from FantasyLeague.scoring_rules.
    If a rule is missing, DEFAULT_SCORING_RULES is used.
    """

    def __init__(self, fantasy_league: FantasyLeague) -> None:
        self.fantasy_league = fantasy_league
        self.rules = self._merge_rules(DEFAULT_SCORING_RULES, fantasy_league.scoring_rules or {})

    @staticmethod
    def _merge_rules(defaults: Dict, overrides: Dict) -> Dict:
        merged = {**defaults}
        for key, value in (overrides or {}).items():
            if isinstance(value, dict) and isinstance(defaults.get(key), dict):
                merged[key] = {**defaults[key], **value}
            else:
                merged[key] = value
        return merged

    def get_matches_for_week(self, match_week: FantasyMatchWeek) -> Iterable[Match]:
        linked = match_week.matches.all()
        if linked.exists():
            return linked
        # Fallback to date window if explicit links are not set
        start_dt = datetime.combine(match_week.start_date, datetime.min.time())
        end_dt = datetime.combine(match_week.end_date, datetime.max.time())
        return Match.objects.filter(date__range=(start_dt, end_dt))

    def _get_player_team_for_match(self, player: Player, match: Match) -> Optional[int]:
        participation = PlayerSeasonParticipation.objects.filter(
            player=player, league=match.season, is_active=True
        ).first()
        return participation.team_id if participation else None

    def _player_was_in_lineup(self, player: Player, match: Match, team_id: Optional[int]) -> bool:
        if team_id is None:
            return False
        return Lineup.objects.filter(match=match, team_id=team_id, players=player).exists()

    def _compute_clean_sheets(self, player: Player, matches: Iterable[Match]) -> int:
        """Count clean sheets for GK/DF based on team conceding zero and player in lineup.

        We rely on Lineup to determine appearance; if not present, we do not award a clean sheet.
        """
        if player.position not in ("GK", "DF", "MF", "FW"):
            return 0

        clean_sheets = 0
        for match in matches:
            team_id = self._get_player_team_for_match(player, match)
            if team_id is None:
                continue
            # Determine conceded by player's team
            conceded = 0
            if match.home_team_id == team_id:
                conceded = match.away_score
            elif match.away_team_id == team_id:
                conceded = match.home_score
            else:
                continue

            if conceded == 0 and self._player_was_in_lineup(player, match, team_id):
                clean_sheets += 1
        return clean_sheets

    def _aggregate_player_match_stats(self, player: Player, matches: Iterable[Match]) -> Dict[str, int]:
        match_ids = [m.id for m in matches]
        if not match_ids:
            return {"goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0, "clean_sheets": 0}

        aggregates = PlayerStats.objects.filter(player=player, match_id__in=match_ids).aggregate(
            goals=Sum("goals"), assists=Sum("assists"), yellow_cards=Sum("yellow_cards"), red_cards=Sum("red_cards")
        )

        # Compute clean sheets from matches/lineups
        clean_sheets = self._compute_clean_sheets(player, [m for m in matches])

        return {
            "goals": aggregates.get("goals") or 0,
            "assists": aggregates.get("assists") or 0,
            "yellow_cards": aggregates.get("yellow_cards") or 0,
            "red_cards": aggregates.get("red_cards") or 0,
            "clean_sheets": clean_sheets,
        }

    def _calculate_points_from_stats(self, player: Player, stats: Dict[str, int]) -> PlayerWeekPoints:
        position = player.position

        goals = stats["goals"]
        assists = stats["assists"]
        yel = stats["yellow_cards"]
        red = stats["red_cards"]
        cs = stats["clean_sheets"]

        per_goal = int(self.rules.get("goal", {}).get(position, 0))
        per_assist = int(self.rules.get("assist", 0))
        per_clean_sheet = int(self.rules.get("clean_sheet", {}).get(position, 0))
        per_yellow = int(self.rules.get("yellow_card", 0))
        per_red = int(self.rules.get("red_card", 0))

        points = goals * per_goal + assists * per_assist + cs * per_clean_sheet + yel * per_yellow + red * per_red
        breakdown = {
            "goals": {"count": goals, "points": goals * per_goal, "per": per_goal},
            "assists": {"count": assists, "points": assists * per_assist, "per": per_assist},
            "clean_sheets": {"count": cs, "points": cs * per_clean_sheet, "per": per_clean_sheet},
            "yellow_cards": {"count": yel, "points": yel * per_yellow, "per": per_yellow},
            "red_cards": {"count": red, "points": red * per_red, "per": per_red},
        }
        return PlayerWeekPoints(total_points=points, breakdown=breakdown)

    def _apply_captain_multiplier(self, fantasy_player: FantasyPlayer, points: int) -> int:
        if points <= 0:
            return points
        if not self.fantasy_league.allow_captain_multiplier:
            return points
        if not fantasy_player.is_captain:
            return points
        multiplier = self.fantasy_league.captain_multiplier or 2
        return points * int(multiplier)

    def _active_in_week_filter(self, week: FantasyMatchWeek) -> Q:
        return Q(active_from__lte=week.end_date) & (Q(active_to__isnull=True) | Q(active_to__gte=week.start_date))

    @transaction.atomic
    def calculate_week(self, match_week: FantasyMatchWeek) -> None:
        matches = list(self.get_matches_for_week(match_week))

        # Calculate per player stats and persist FantasyPlayerStats
        league_teams: List[FantasyTeam] = list(self.fantasy_league.teams.all())

        team_week_points: Dict[int, int] = {}

        for team in league_teams:
            week_points_sum = 0
            active_players: List[FantasyPlayer] = list(
                team.fantasy_players.filter(self._active_in_week_filter(match_week)).select_related("player")
            )

            for fplayer in active_players:
                player = fplayer.player
                stats = self._aggregate_player_match_stats(player, matches)
                week_points = self._calculate_points_from_stats(player, stats)
                final_points = self._apply_captain_multiplier(fplayer, week_points.total_points)

                FantasyPlayerStats.objects.update_or_create(
                    fantasy_player=fplayer,
                    fantasy_match_week=match_week,
                    defaults={"points": final_points, "breakdown": week_points.breakdown},
                )

                week_points_sum += final_points

            team_week_points[team.id] = week_points_sum

        # Update leaderboard weekly and overall
        self._update_leaderboard(match_week, team_week_points)

    def _update_leaderboard(self, match_week: FantasyMatchWeek, week_points_by_team_id: Dict[int, int]) -> None:
        # Update/insert weekly entries and compute cumulative
        for team_id, points_week in week_points_by_team_id.items():
            team = FantasyTeam.objects.get(id=team_id)

            # Compute new cumulative total from previous overall entry
            overall, _ = FantasyLeaderboard.objects.get_or_create(
                fantasy_team=team, is_overall=True, defaults={"cumulative_points": 0}
            )

            cumulative_points = (overall.cumulative_points or 0) + int(points_week)

            # Weekly entry for this week
            FantasyLeaderboard.objects.update_or_create(
                fantasy_team=team,
                fantasy_match_week=match_week,
                defaults={
                    "points_week": int(points_week),
                    "cumulative_points": cumulative_points,
                    "is_overall": False,
                },
            )

            # Update overall
            overall.cumulative_points = cumulative_points
            overall.save(update_fields=["cumulative_points", "updated_at"])

        # Re-rank weekly entries (by points_week desc, then team name)
        weekly_entries = list(FantasyLeaderboard.objects.filter(fantasy_match_week=match_week, is_overall=False).select_related("fantasy_team"))
        weekly_entries.sort(key=lambda e: (-e.points_week, e.fantasy_team.name))
        self._assign_ranks(weekly_entries)

        # Re-rank overall entries (by cumulative_points desc)
        overall_entries = list(FantasyLeaderboard.objects.filter(is_overall=True).select_related("fantasy_team"))
        overall_entries.sort(key=lambda e: (-e.cumulative_points, e.fantasy_team.name))
        self._assign_ranks(overall_entries)

    def _assign_ranks(self, entries: List[FantasyLeaderboard]) -> None:
        current_rank = 0
        last_points: Optional[int] = None
        for index, entry in enumerate(entries, start=1):
            points_value = entry.points_week if not entry.is_overall else entry.cumulative_points
            if last_points is None or points_value < last_points:
                current_rank = index
            entry.rank = current_rank
            last_points = points_value
        FantasyLeaderboard.objects.bulk_update(entries, ["rank", "updated_at"])  # updated_at auto-updates on save; bulk_update ignores


def example_scoring_rules() -> Dict:
    """Return a sample scoring rules JSON payload to store in FantasyLeague.scoring_rules.

    Defaults match the specification and can be tweaked per league via admin.
    """
    return {
        "goal": {"GK": 6, "DF": 6, "MF": 5, "FW": 4},
        "assist": 3,
        "clean_sheet": {"GK": 4, "DF": 4, "MF": 1, "FW": 0},
        "yellow_card": -1,
        "red_card": -3,
    }


