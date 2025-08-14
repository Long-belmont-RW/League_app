from django.contrib import admin

from .models import (
    FantasyLeague,
    FantasyTeam,
    FantasyPlayer,
    FantasyMatchWeek,
    FantasyPlayerStats,
    FantasyLeaderboard,
    FantasyTransfer,
)
from .services import example_scoring_rules


@admin.register(FantasyLeague)
class FantasyLeagueAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "max_team_size", "budget_cap", "transfer_limit", "max_per_real_team")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    actions = ["seed_default_scoring_rules"]

    def seed_default_scoring_rules(self, request, queryset):
        updated = 0
        for league in queryset:
            league.scoring_rules = example_scoring_rules()
            league.save(update_fields=["scoring_rules", "updated_at"])
            updated += 1
        self.message_user(request, f"Seeded default scoring rules for {updated} league(s)")
    seed_default_scoring_rules.short_description = "Seed default scoring rules"


class FantasyPlayerInline(admin.TabularInline):
    model = FantasyPlayer
    extra = 0
    raw_id_fields = ("player",)
    fields = ("player", "price_at_purchase", "is_captain", "is_vice_captain", "active_from", "active_to")


@admin.register(FantasyTeam)
class FantasyTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "fantasy_league", "balance", "created_at")
    list_filter = ("fantasy_league",)
    search_fields = ("name", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [FantasyPlayerInline]


@admin.register(FantasyMatchWeek)
class FantasyMatchWeekAdmin(admin.ModelAdmin):
    list_display = ("fantasy_league", "index", "name", "start_date", "end_date", "deadline_at")
    list_filter = ("fantasy_league",)
    search_fields = ("name",)
    filter_horizontal = ("matches",)


@admin.register(FantasyPlayerStats)
class FantasyPlayerStatsAdmin(admin.ModelAdmin):
    list_display = ("fantasy_player", "fantasy_match_week", "points")
    list_filter = ("fantasy_match_week",)
    search_fields = ("fantasy_player__player__full_name", "fantasy_player__fantasy_team__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FantasyLeaderboard)
class FantasyLeaderboardAdmin(admin.ModelAdmin):
    list_display = ("fantasy_team", "fantasy_match_week", "is_overall", "points_week", "cumulative_points", "rank", "updated_at")
    list_filter = ("fantasy_match_week", "is_overall", "fantasy_team__fantasy_league")
    search_fields = ("fantasy_team__name", "fantasy_team__user__username", "fantasy_team__user__email")


@admin.register(FantasyTransfer)
class FantasyTransferAdmin(admin.ModelAdmin):
    list_display = ("fantasy_team", "fantasy_match_week", "player_in", "player_out", "cost", "created_at")
    list_filter = ("fantasy_match_week", "fantasy_team__fantasy_league")
    search_fields = ("fantasy_team__name", "player_in__first_name", "player_in__last_name")


