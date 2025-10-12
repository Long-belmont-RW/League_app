from django.contrib import admin
from .models import User, UserProfile, Notification

admin.site.register(User)
admin.site.register(Notification)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "favorite_teams_count", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("favorite_teams",)
    readonly_fields = ("created_at", "updated_at")
    fields = ("user", "bio", "image", "favorite_teams", "created_at", "updated_at")

    def favorite_teams_count(self, obj):
        return obj.favorite_teams.count()
    favorite_teams_count.short_description = "Favorites"
