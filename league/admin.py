from django.contrib import admin
from .models import Player, PlayerStats, Coach, Team, League, TeamSeasonParticipation, Match, PlayerSeasonParticipation,\
      CoachSeasonParticipation, Lineup

@admin.register(TeamSeasonParticipation)
class TeamSeasonParticipaationAdmin(admin.ModelAdmin):
    pass

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    pass


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    pass

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

