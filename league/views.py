from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum
from django.contrib import messages


from .models import \
    (League, Team, TeamSeasonParticipation, Match, PlayerSeasonParticipation)

from league.forms import MatchForm
from league.services import update_league_table



def home(request):
    return render (request, 'home.html')

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
                    participations.update_totals()
            
           
            
            messages.success(request, f"Match {'updated' if is_edit else 'created'} successfully.")
            return redirect('match_list')
        else:
            messages.error(request, "There was an error with your submission.")
            print(form.errors) 
    
    else: 

        form  = MatchForm(instance=match)
    
    context = {
        'form':form,
        'is_edit': is_edit,
        'match': match
    }

    return render(request, 'match_form.html', context)

def delete_match(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    if request.method == 'POST':
        match.delete()
        messages.success(request, f"{match} was successfully deleted.")
        return redirect('match_list')

    return render(request, 'delete_match.html', {'match': match})



def match_list_view(request):
    matches = Match.objects.select_related('home_team', 'away_team', 'season').order_by('-date')
    return render(request, 'match_list.html', {'matches': matches})


def top_stats_view(request, league_id):
    league = League.objects.get(id=league_id)

    top_scorers = PlayerSeasonParticipation.objects.filter(league=league)\
        .select_related('player')\
        .annotate(total_goals=Sum('goals'))\
        .order_by('-total_goals')[:10]
    
    top_assisters = PlayerSeasonParticipation.objects.filter(league=league)\
        .select_related('player')\
        .annotate(total_assists=Sum('assists'))\
        .order_by('-total_assists')[:10]

    context = {
        'league': league,
        'top_scorers': top_scorers,
        'top_assisters': top_assisters
    }

    return render(request, 'top_stats.html', context)






