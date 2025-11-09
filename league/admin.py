from django.contrib import admin
from .models import (
    Player, PlayerStats, Coach, Team, League, TeamSeasonParticipation, Match,
    PlayerSeasonParticipation, CoachSeasonParticipation, Lineup, LineupPlayer,
    TeamOfTheWeek, TeamOfTheWeekPlayer, MatchEvent
)

# Inlines
class PlayerSeasonParticipationInline(admin.TabularInline):
    model = PlayerSeasonParticipation
    extra = 1
    raw_id_fields = ('player',)

class CoachSeasonParticipationInline(admin.TabularInline):
    model = CoachSeasonParticipation
    extra = 1
    raw_id_fields = ('coach',)

class TeamSeasonParticipationInline(admin.TabularInline):
    model = TeamSeasonParticipation
    extra = 1
    readonly_fields = ('points', 'goals_scored', 'goals_conceded', 'wins', 'losses', 'draws', 'matches_played', 'goal_difference')

class LineupPlayerInline(admin.TabularInline):
    model = LineupPlayer
    extra = 11
    raw_id_fields = ('player',)

class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 1
    raw_id_fields = ('player',)

class TeamOfTheWeekPlayerInline(admin.TabularInline):
    model = TeamOfTheWeekPlayer
    extra = 11
    raw_id_fields = ('player',)

class LineupInline(admin.TabularInline):
    model = Lineup
    extra = 0
    raw_id_fields = ('team',)
    readonly_fields = ('formation',)

# ModelAdmins
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "position", "price", "is_active")
    list_filter = ("position", "is_active")
    search_fields = ("first_name", "last_name")
    inlines = [PlayerSeasonParticipationInline]

@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("first_name", "last_name")
    inlines = [CoachSeasonParticipationInline]

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [TeamSeasonParticipationInline]

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("year", "session", "is_active")
    list_filter = ("year", "session", "is_active")
    inlines = [TeamSeasonParticipationInline]

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('season', 'match_day', 'home_team', 'away_team', 'home_score', 'away_score', 'date', 'status')
    list_filter = ('status', 'season', 'match_day')
    search_fields = ('home_team__name', 'away_team__name')
    raw_id_fields = ('season', 'home_team', 'away_team')
    inlines = [MatchEventInline, LineupInline]
    fieldsets = (
        ('Match Info', {
            'fields': ('season', 'match_day', 'date', 'status')
        }),
        ('Teams', {
            'fields': ('home_team', 'away_team')
        }),
        ('Score', {
            'fields': ('home_score', 'away_score')
        }),
        ('Timestamps', {
            'fields': ('actual_kickoff_time',)
        }),
    )
    readonly_fields = ('actual_kickoff_time',)

@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ('player', 'match', 'goals', 'assists', 'yellow_cards', 'red_cards')
    search_fields = ('player__first_name', 'player__last_name', 'match__home_team__name', 'match__away_team__name')
    raw_id_fields = ('player', 'match')

@admin.register(PlayerSeasonParticipation)
class PlayerSeasonParticipationAdmin(admin.ModelAdmin):
    list_display = ('player', 'team', 'league', 'is_active', 'goals', 'assists')
    list_filter = ('league', 'team', 'is_active')
    search_fields = ('player__first_name', 'player__last_name', 'team__name')
    raw_id_fields = ('player', 'team', 'league')

@admin.register(CoachSeasonParticipation)
class CoachSeasonParticipationAdmin(admin.ModelAdmin):
    list_display = ('coach', 'team', 'league')
    list_filter = ('league', 'team')
    search_fields = ('coach__first_name', 'coach__last_name', 'team__name')
    raw_id_fields = ('coach', 'team', 'league')

@admin.register(TeamSeasonParticipation)
class TeamSeasonParticipationAdmin(admin.ModelAdmin):
    list_display = ('team', 'league', 'points', 'matches_played', 'wins', 'losses', 'draws')
    list_filter = ('league',)
    search_fields = ('team__name',)
    raw_id_fields = ('team', 'league')
    readonly_fields = ('points', 'goals_scored', 'goals_conceded', 'wins', 'losses', 'draws', 'matches_played', 'goal_difference')

@admin.register(Lineup)
class LineupAdmin(admin.ModelAdmin):
    list_display = ('match', 'team', 'formation')
    list_filter = ('match__season',)
    raw_id_fields = ('match', 'team')
    inlines = [LineupPlayerInline]

@admin.register(TeamOfTheWeek)
class TeamOfTheWeekAdmin(admin.ModelAdmin):
    inlines = [TeamOfTheWeekPlayerInline]
    list_display = ('league', 'week_number')
    list_filter = ('league', 'week_number')
    raw_id_fields = ('league',)

# Registering models that don't need a custom admin
admin.site.register(LineupPlayer)

admin.site.site_header = "League Management Admin"
admin.site.site_title = "League Management Admin"
admin.site.index_title = "Welcome to the League Management Admin"
