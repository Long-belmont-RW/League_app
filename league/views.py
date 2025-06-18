from django.shortcuts import render, get_object_or_404
from .models import League, Team, TeamSeasonParticipation

# Create your views here.


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
    team = get_object_or_404(Team, id=team_id)

    context = {
        'team':team
    }

    return render(request, 'team_details.html', context)