# league/signals.py
from django.db.models.signals import post_save, post_delete, pre_save, m2m_changed
from django.dispatch import receiver
from .models import PlayerStats, Match, TeamSeasonParticipation, MatchStatus, Lineup
from django.db.models import Q, F
from django.core.mail import send_mail
from users.models import UserProfile, Notification
from users.utils import push_user_notification

@receiver(pre_save, sender=Match)
def store_old_match_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Match.objects.get(pk=instance.pk).status
        except Match.DoesNotExist:
            instance._old_status = None
    
    else:
        instance._old_status = None

@receiver([post_save, post_delete], sender=PlayerStats)
def update_player_season_stats(sender, instance, **kwargs):
    """ Update player season stats after player stats are saved or deleted.
    This updates the player's participation record with total goals, assists,
    and other relevant statistics."""
    
    participation = instance.player_participation
    if participation:
        participation.update_totals()



@receiver([post_save, post_delete], sender=Match)
def update_team_season_stats(sender, instance, **kwargs):
    """ Update team season stats after a match is saved or deleted.
    This calculates wins, losses, draws, points, goals scored, and goals conceded
    for each team in the league of the match."""

    #Check previous status if available
    old_status = getattr(instance, '_old_status',None)
    new_status = instance.status

    #Trigger update if status changes to or from finished

    if (old_status == MatchStatus.FINISHED or new_status == MatchStatus.FINISHED) and old_status != new_status:
        home_team_participation = TeamSeasonParticipation.objects.filter(
            league=instance.season, team=instance.home_team
        ).first()
        away_team_participation = TeamSeasonParticipation.objects.filter(
            league=instance.season, team=instance.away_team
        ).first()

        if home_team_participation:
            home_team_participation.update_stats()
        
        if away_team_participation:
            away_team_participation.update_stats()

# A separate signal for deletion is cleaner
@receiver(post_delete, sender=Match)
def update_team_season_stats_on_delete(sender, instance, **kwargs):
    """
    Update team season stats if a finished match is deleted.
    """
    # Only act if the deleted match was finished
    if instance.status == MatchStatus.FINISHED:
        
        home_team_participation = TeamSeasonParticipation.objects.filter(
            league=instance.season, team=instance.home_team
        ).first()
        away_team_participation = TeamSeasonParticipation.objects.filter(
            league=instance.season, team=instance.away_team
        ).first()

        if home_team_participation:
            home_team_participation.update_stats()
        
        if away_team_participation:
            away_team_participation.update_stats()


@receiver(m2m_changed, sender=Lineup.players.through)
def notify_players_on_lineup_change(sender, instance: Lineup, action, reverse, pk_set, **kwargs):
    """Notify players when they are added to or removed from a lineup."""
    if action not in {"post_add", "post_remove"}:
        return

    match = instance.match
    team = instance.team
    added = action == "post_add"

    for player_pk in pk_set:
        try:
            # Find the user linked to this Player via UserProfile
            user_profile = UserProfile.objects.select_related('user').get(player_id=player_pk)
            user = user_profile.user
        except UserProfile.DoesNotExist:
            continue

        title = "You are in the lineup" if added else "You were removed from the lineup"
        message = (
            f"{team.name} vs {match.away_team if team == match.home_team else match.home_team} on "
            f"{match.date.strftime('%Y-%m-%d %H:%M')} — status: {'Selected' if added else 'Removed'}."
        )

        # Create in-app notification
        note = Notification.objects.create(user=user, title=title, message=message)

        # Push realtime update
        try:
            push_user_notification(user.id, {"title": note.title, "message": note.message})
        except Exception:
            pass

        # Send email notification (best moved to a background task in production)
        try:
            send_mail(
                subject=title,
                message=message,
                from_email='noreply@league.local',
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass