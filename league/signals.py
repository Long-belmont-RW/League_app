# league/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import PlayerStats, Match, TeamSeasonParticipation, MatchStatus
from django.db.models import Q, F

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