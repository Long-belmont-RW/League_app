from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Q
from django.db import transaction
from django.contrib import messages


from .models import \
    (League, Team, TeamSeasonParticipation, Match, 
     PlayerSeasonParticipation, PlayerStats)

from league.forms import MatchForm, PlayerStatsFormSet
from league.services import update_league_table

import logging
logger = logging.getLogger(__name__)


def home(request):
    #get the latest league
    latest_league = League.objects.order_by('-year', '-id').first()
    return render (request, 'home.html', {
        'latest_league': latest_league,})

def leagues(request):
    leagues = League.objects.all()

    context = {
        'leagues': leagues
    }

    return render(request, 'leagues.html', context)

def league_table_view(request, league_id):
    league = get_object_or_404(League, id=league_id)
    standings = TeamSeasonParticipation.objects.filter(league=league).select_related('team')

    context = {
        'league':league,
        'standings':standings,
    }

    return render(request, 'league_table.html', context)

def team_view(request):
    teams = Team.objects.all()
    
    

    context = {
        'teams': teams
    }

    return render(request, 'teams.html', context)

def team(request, team_id):
    """Gets the details of a registered team"""

    team = get_object_or_404(Team, id=team_id)
    league = League.objects.all().first()
    current_players = team.get_current_players(league)

    context = {
        'team':team,
        'current_players':current_players
    }

    return render(request, 'team_details.html', context)


def match_form_view(request, match_id=None):
    """A form to create match objects"""
    if match_id:
        match = get_object_or_404(Match, id=match_id)
        is_edit = True
    
    else:
        match=None
        is_edit = False
    
    if request.method == 'POST':
        form = MatchForm(request.POST, instance=match)
        if form.is_valid():
            match = form.save()
            if match.status == "FIN":
                #update League table
                update_league_table(match.season)

                #find all players who played in this match
                participations = PlayerSeasonParticipation.objects.filter(
                    player_stats__match=match
                ).distinct()

                for participation in participations:
                    participation.update_totals()
            
           
            
            messages.success(request, f"Match {'updated' if is_edit else 'created'} successfully.")
            return redirect('match_list')
        else:
            messages.error(request, "There was an error with your submission.")
            logger.info(form.errors) 
    
    else: 

        form  = MatchForm(instance=match)
    
    context = {
        'form':form,
        'is_edit': is_edit,
        'match': match
    }

    return render(request, 'match_form.html', context)

def delete_match(request, match_id):
    """A simple view to delete matches"""
    match = get_object_or_404(Match, id=match_id)
    if request.method == 'POST':
        match.delete()
        messages.success(request, f"{match} was successfully deleted.")
        return redirect('match_list')

    return render(request, 'delete_match.html', {'match': match})



def match_list_view(request):
    """A simple view to list out current matches"""

    matches = Match.objects.select_related('home_team', 'away_team', 'season').order_by('-date')

    # Get Search parameters
    team_search = request.GET.get('team_search', '').strip()
    match_day_filter = request.GET.get('match_day', '').strip() 
    league_filter = request.GET.get('league', '').strip()

    #Base queryset
    upcoming_matches = Match.objects.select_related('home_team', 'away_team', 'season').filter(status='SCH')
    finished_matches = Match.objects.select_related('home_team', 'away_team', 'season').filter(status='FIN')

    # Filter by team name
    if team_search:
        team_filter = Q(home_team__name__icontains=team_search) | Q(away_team__name__icontains=team_search )
        upcoming_matches = upcoming_matches.filter(team_filter)
        finished_matches = finished_matches.filter(team_filter)

    # Filter by match day
    if match_day_filter:
        try:
            match_day = int(match_day_filter)
            if match_day < 1 or match_day > 10:  # Assuming a maximum of 10 match days
                messages.error(request, "Match day must be between 1 and 10.")
            else:
                upcoming_matches = upcoming_matches.filter(match_day=match_day)
                finished_matches = finished_matches.filter(match_day=match_day)
        except ValueError:
            messages.error(request, "Invalid match day value.")
    
    # Filter by league
    if league_filter:   
        try:
            league = League.objects.get(id=league_filter)
            upcoming_matches = upcoming_matches.filter(season=league)
            finished_matches = finished_matches.filter(season=league)
        except League.DoesNotExist:
            messages.error(request, "Invalid league selected.")
    
    # Order matches by date
    upcoming_matches = upcoming_matches.order_by('date')
    finished_matches = finished_matches.order_by('-date')

    #Get all leagues for the filter dropdown
    leagues = League.objects.all().order_by('-year', 'session')

    #Get distinct matchdays for the filter dropdown
    match_days = Match.objects.values_list('match_day', flat=True).distinct().order_by('match_day')

    context = {
        'upcoming_matches': upcoming_matches,
        'finished_matches': finished_matches,
        'leagues': leagues,
        'match_days': match_days,
        'team_search': team_search,
        'match_day_filter': match_day_filter,
        'league_filter': league_filter,
    }

    return render(request, 'match_list.html', context)


def top_stats_view(request, league_id):
    """View to display season statistics"""
    league = League.objects.get(id=league_id)

    top_scorers = PlayerSeasonParticipation.objects.filter(
        league=league,
        goals__gt=0  # Only include players with goals
    ).select_related('player').order_by('-goals')[:10]
    
    top_assisters = PlayerSeasonParticipation.objects.filter(
        league=league,
        assists__gt=0  # Only include players with assists
    ).select_related('player').order_by('-assists')[:10]

    context = {
        'league': league,
        'top_scorers': top_scorers,
        'top_assisters': top_assisters
    }

    return render(request, 'top_stats.html', context)


def edit_player_stats_view(request, match_id):
    """
    Edit player statistics for a specific match.
    Create PlayerStats objects for all active players from both teams if they don't exist
    """

    match = get_object_or_404(Match, id=match_id)
    logger.info(f"Match: {match}")
    logger.info(f"Match season: {match.season}")
    logger.info(f"Home team: {match.home_team}")
    logger.info(f"Away team: {match.away_team}")
    

    #Get all active players that participated in the match
    participations = PlayerSeasonParticipation.objects.filter(
        league=match.season,
        team__in=[match.home_team, match.away_team],
        is_active=True,
    ).select_related('player', 'team')

    logger.info(f"Found {participations.count()} season particpation objects")

    #Create PlayerStats objects for players who don't have yet
    for participation in participations:
        
        PlayerStats.objects.get_or_create(
            match=match,
            player=participation.player,
            defaults={
                'player_participation': participation,
                'goals': 0,
                'assists': 0,
                'yellow_cards': 0,
                'red_cards': 0,
            
            }
        )

        

    #create queryset for the formset
    queryset = PlayerStats.objects.filter(
        match=match,
        player__in=[p.player for p in participations]
    ).select_related('player', 'player_participation'). order_by('player__first_name')


    if request.method == 'POST':
        formset = PlayerStatsFormSet(request.POST, queryset=queryset)

        if formset.is_valid():
            try:
                with transaction.atomic():
                    #save all the forms in the formset
                    saved_forms = formset.save()


                    #update the stats of players who participated
                    for instance in saved_forms:
                        instance.player_participation.update_totals()
                    
                    messages.success(request, f'Player statistics updated successfully for {match}')
                return redirect('match_list')
            
            except Exception as e:
                messages.error(request, 'An error occurred while saving the statistics. Please try again.')

                # log the error for debugging
                logger.error(f"Error saving player stats for match {match_id}: {e}") 
            
        else:
            messages.error(request, 'Please correct the erros in the form.')
            
   
    else: #GET 
        formset = PlayerStatsFormSet(queryset=queryset)
    

    context = {
        'formset': formset,
        'match': match,
        
    }


    return render(request, 'edit_player_stats.html', context)