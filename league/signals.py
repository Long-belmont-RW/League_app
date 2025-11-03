from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from .models import Match, TeamSeasonParticipation, MatchStatus, PlayerStats, PlayerSeasonParticipation

def _apply_match_results(match, multiplier=1):
    """
    Applies or reverts a match's results to the league table.
    A multiplier of 1 adds the stats, -1 subtracts them.
    """
    if not all([match.home_team, match.away_team, match.season]):
        return

    home_stats, _ = TeamSeasonParticipation.objects.get_or_create(team=match.home_team, league=match.season)
    away_stats, _ = TeamSeasonParticipation.objects.get_or_create(team=match.away_team, league=match.season)

    # Update goals
    home_stats.goals_scored += match.home_score * multiplier
    home_stats.goals_conceded += match.away_score * multiplier
    away_stats.goals_scored += match.away_score * multiplier
    away_stats.goals_conceded += match.home_score * multiplier

    # Update matches played
    home_stats.matches_played += 1 * multiplier
    away_stats.matches_played += 1 * multiplier

    # Update points, wins, losses, draws
    if match.home_score > match.away_score:
        home_stats.points += 3 * multiplier
        home_stats.wins += 1 * multiplier
        away_stats.losses += 1 * multiplier
    elif match.away_score > match.home_score:
        away_stats.points += 3 * multiplier
        away_stats.wins += 1 * multiplier
        home_stats.losses += 1 * multiplier
    else:
        home_stats.points += 1 * multiplier
        away_stats.points += 1 * multiplier
        home_stats.draws += 1 * multiplier
        away_stats.draws += 1 * multiplier

    home_stats.save()
    away_stats.save()

@receiver(pre_save, sender=Match)
def store_old_match_state(sender, instance, **kwargs):
    """Store the old state of the match instance before it's saved."""
    if instance.pk:
        try:
            instance._old_state = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._old_state = None
    else:
        instance._old_state = None

@receiver(post_save, sender=Match)
def update_stats_on_match_save(sender, instance, created, **kwargs):
    """
    Update league stats based on match status changes.
    This signal handler covers:
    - A match becoming FINISHED.
    - A FINISHED match changing status.
    - A FINISHED match's score being updated.
    """
    if kwargs.get('raw', False): # Ignore fixture loading
        return

    old_state = getattr(instance, '_old_state', None)

    # Revert old state if it existed and was FINISHED
    if old_state and old_state.status == MatchStatus.FINISHED:
        _apply_match_results(old_state, multiplier=-1)

    # Apply new state if it is FINISHED
    if instance.status == MatchStatus.FINISHED:
        _apply_match_results(instance, multiplier=1)

@receiver(pre_delete, sender=Match)
def revert_stats_on_delete(sender, instance, **kwargs):
    """Revert league stats if a FINISHED match is deleted."""
    if instance.status == MatchStatus.FINISHED:
        _apply_match_results(instance, multiplier=-1)


@receiver(post_save, sender=PlayerStats)
def update_player_season_stats_on_save(sender, instance, created, **kwargs):
    """
    Updates PlayerSeasonParticipation aggregated stats when a PlayerStats object is saved.
    """
    if kwargs.get('raw', False): # Ignore fixture loading
        return

    # Get the PlayerSeasonParticipation instance
    player_psp = PlayerSeasonParticipation.objects.filter(
        player=instance.player,
        league=instance.match.season
    ).first()

    if player_psp:
        player_psp.update_totals()

@receiver(post_delete, sender=PlayerStats)
def update_player_season_stats_on_delete(sender, instance, **kwargs):
    """
    Updates PlayerSeasonParticipation aggregated stats when a PlayerStats object is deleted.
    """
    if kwargs.get('raw', False): # Ignore fixture loading
        return

    # Get the PlayerSeasonParticipation instance
    player_psp = PlayerSeasonParticipation.objects.filter(
        player=instance.player,
        league=instance.match.season
    ).first()

    if player_psp:
        player_psp.update_totals()
