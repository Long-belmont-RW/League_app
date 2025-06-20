from league.models import Match, TeamSeasonParticipation, Team, League, MatchStatus
from django.db.models import Q


def update_league_table(league: League):
    """Recalculate team stats for a league based on all FINISHED matches."""
    #Clear the old stats
    team_participations = TeamSeasonParticipation.objects.filter(league=league)
    team_participations.update(
        points=0,
        wins=0,
        draws=0,
        losses=0,
        goals_scored=0,
        goals_conceded=0,
        matches_played=0,
    )

    #Get all Finished matches in this league

    finished_matches = Match.objects.filter(season=league, status=MatchStatus.FINISHED)

    for match in finished_matches:
        home = match.home_team
        away = match.away_team
        home_score = match.home_score
        away_score = match.away_score



        #Ensure Each team is registered in the league

        home_stats, _ = TeamSeasonParticipation.objects.get(team=home, league=league)

        away_stats, _ = TeamSeasonParticipation.objects.get_or_create(team=away, league=league)

        # Update basic stats
        home_stats.matches_played += 1
        away_stats.matches_played += 1

        home_stats.goals_scored += home_score
        home_stats.goals_conceded += away_score

        away_stats.goals_scored += away_score
        away_stats.goals_conceded += home_score

        # Determine match result
        if home_score > away_score:
            home_stats.wins += 1
            home_stats.points += 3
            away_stats.losses += 1
        elif home_score < away_score:
            away_stats.wins += 1
            away_stats.points += 3
            home_stats.losses += 1
        else:
            home_stats.draws += 1
            away_stats.draws += 1
            home_stats.points += 1
            away_stats.points += 1

        home_stats.save()
        away_stats.save()

    return True