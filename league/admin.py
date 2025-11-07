from django.contrib import admin
from .models import (
    Player, PlayerStats, Coach, Team, League, TeamSeasonParticipation, Match,
    PlayerSeasonParticipation, CoachSeasonParticipation, Lineup, LineupPlayer,
    TeamOfTheWeek, TeamOfTheWeekPlayer
)

@admin.register(TeamSeasonParticipation)
class TeamSeasonParticipaationAdmin(admin.ModelAdmin):
    pass

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "position", "price", "is_active")
    list_filter = ("position", "is_active")
    search_fields = ("first_name", "last_name")


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    pass

class TeamOfTheWeekPlayerInline(admin.TabularInline):
    model = TeamOfTheWeekPlayer
    extra = 11

# @admin.register(TeamOfTheWeek)
# class TeamOfTheWeekAdmin(admin.ModelAdmin):
#     inlines = [TeamOfTheWeekPlayerInline]
#     list_display = ('league', 'week_number')
#     list_filter = ('league', 'week_number')

admin.site.register(Coach)
admin.site.register(Team)
admin.site.register(League)

admin.site.register(Match)

admin.site.register(PlayerSeasonParticipation)
admin.site.site_header = "League Management Admin"
admin.site.site_title = "League Management Admin"
admin.site.index_title = "Welcome to the League Management Admin"

admin.site.register(CoachSeasonParticipation)
admin.site.register(Lineup)
admin.site.register(LineupPlayer)

