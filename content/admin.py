from django.contrib import admin, messages
from django.utils import timezone
from .models import Invitation

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'team', 'role', 'is_accepted', 'is_expired', 'created_at', 'expires_at', 'sent_by')
    list_filter = ('is_accepted', 'role', 'team')
    search_fields = ('email', 'team__name', 'sent_by__email')
    readonly_fields = ('token', 'created_at', 'accepted_at')
    date_hierarchy = 'created_at'
    list_per_page = 25
    raw_id_fields = ('team', 'sent_by')
    actions = ['resend_invitations']

    fieldsets = (
        ('Invitation Details', {
            'fields': ('email', 'team', 'role', 'sent_by')
        }),
        ('Status', {
            'fields': ('is_accepted', 'accepted_at', 'token')
        }),
        ('Important Dates', {
            'fields': ('created_at', 'expires_at')
        }),
    )

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired?'

    def resend_invitations(self, request, queryset):
        # A placeholder for the resend logic
        # In a real implementation, you would call your service to send emails.
        for invitation in queryset:
            # Dummy logic: just update expires_at for demonstration
            invitation.expires_at = timezone.now() + timezone.timedelta(days=3)
            invitation.save()
        self.message_user(request, f"{queryset.count()} invitations have been notionally resent and their expiry updated.", messages.SUCCESS)
    resend_invitations.short_description = "Resend selected invitations"