from django.contrib import admin
from .models import Player, PlayerStats, Coach, Team, League


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    pass


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    pass

admin.site.register(Coach)
admin.site.register(Team)
admin.site.register(League)

