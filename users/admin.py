from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Notification

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    raw_id_fields = ('coach', 'player', 'favorite_teams')

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'role')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)
    
    # Add custom fields to the fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('birth', 'gender', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('birth', 'gender', 'role')}),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__email', 'title')
    raw_id_fields = ('user',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "favorite_teams_count", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("favorite_teams",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ('user', 'coach', 'player')
    fieldsets = (
        (None, {
            'fields': ('user', 'bio', 'image')
        }),
        ('Related Models', {
            'fields': ('coach', 'player')
        }),
        ('Favorites', {
            'fields': ('favorite_teams',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def favorite_teams_count(self, obj):
        return obj.favorite_teams.count()
    favorite_teams_count.short_description = "Favorites"
