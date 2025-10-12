# league/views.py
import json
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import Sum, Q, F, Prefetch

from .models import League, Lineup, Team, Match, Player, PlayerSeasonParticipation, PlayerStats, MatchStatus,     TeamSeasonParticipation, CoachSeasonParticipation, LineupPlayer
from .forms import LineupPlayerForm, MatchForm, PlayerStatsForm, PlayerStatsFormSet, LineupFormSet, MatchEventForm, ValidatingLineupFormSet
from .utils import get_league_standings
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django import forms as django_forms

# Home View (Displays recent matches and top scorers)
def home(request):
    active_league = League.objects.filter(is_active=True).first()
    matches = Match.objects.none()
    top_scorers = PlayerSeasonParticipation.objects.none()
    if active_league:
        matches = Match.objects.filter(season=active_league).select_related('home_team', 'away_team').order_by('-date')[:5]
        top_scorers = PlayerSeasonParticipation.objects.filter(
            league=active_league, is_active=True
        ).select_related('player').order_by('-goals')[:5]
    rendered = render_to_string('home.html', {
        'matches': matches,
        'top_scorers': top_scorers,
        'active_league': active_league,
    }, request=request)
    return HttpResponse(rendered)


# Leagues List View
class LeaguesView(ListView):
    model = League
    template_name = 'leagues.html'
    context_object_name = 'leagues'
    paginate_by = 10

# League Table View
def league_table_view(request, league_id):
    league = get_object_or_404(League, id=league_id)
    standings = get_league_standings(league)
    rendered = render_to_string('league_table.html', {
        'league': league,
        'standings': standings,
    }, request=request)
    return HttpResponse(rendered)

# Top Stats View (Leaderboard for top scorers, assisters, etc.)
class TopStatsView(ListView):
    template_name = 'top_stats.html'
    context_object_name = 'players'

    def get_queryset(self):
        league_id = self.kwargs['league_id']
        return PlayerSeasonParticipation.objects.filter(
            league_id=league_id, is_active=True
        ).select_related('player', 'team').annotate(
            total_goals=F('goals'),
            total_assists=F('assists')
        ).order_by('-total_goals')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['league'] = League.objects.get(id=self.kwargs['league_id'])
        return context

# Teams List View
class TeamView(ListView):
    model = Team
    template_name = 'teams.html'
    context_object_name = 'teams'
    paginate_by = 10

# Team Detail View
def team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    active_league = League.objects.filter(is_active=True).first()
    current_players = team.get_current_players(active_league)
    matches = team.all_matches().filter(season=active_league).select_related('home_team', 'away_team')
    rendered = render_to_string('team_details.html', {
        'team': team,
        'current_players': current_players,
        'matches': matches,
        'active_league': active_league,
    }, request=request)

    return HttpResponse(rendered)

# Match List View (with HTMX filtering)
class MatchListView(ListView):
    model = Match
    template_name = 'match_list.html'
    paginate_by = 10
    context_object_name = 'matches'

    def get_queryset(self):
        """Build the base queryset with optimizations"""
        queryset = Match.objects.select_related(
            'season', 'home_team', 'away_team'
        ).prefetch_related(
            Prefetch(
                'home_team__teamseasonparticipation_set',
                queryset=TeamSeasonParticipation.objects.select_related('league'),
                to_attr='current_season_participation'
            ),
            Prefetch(
                'away_team__teamseasonparticipation_set',
                queryset=TeamSeasonParticipation.objects.select_related('league'),
                to_attr='current_season_participation'
            ),
            'playerstats_set__player'
        )
        queryset = queryset.filter(season__is_active=True)
        return queryset

    def get_filtered_queryset(self):
        """Apply filters based on request parameters"""
        queryset = self.get_queryset()
        team_search = self.request.GET.get('team_search', '').strip()
        if team_search:
            queryset = queryset.filter(
                Q(home_team__name__icontains=team_search) |
                Q(away_team__name__icontains=team_search)
            )
        match_day = self.request.GET.get('match_day')
        if match_day:
            try:
                match_day = int(match_day)
                queryset = queryset.filter(match_day=match_day)
            except (ValueError, TypeError):
                pass
        league_id = self.request.GET.get('league')
        if league_id:
            try:
                league_id = int(league_id)
                queryset = queryset.filter(season_id=league_id)
            except (ValueError, TypeError):
                pass
        return queryset

    def get_matches_by_status(self, queryset):
        """Split matches by status"""
        matches_data = {
            'scheduled': [],
            'live': [],
            'finished': []
        }
        for match in queryset:
            if match.status == MatchStatus.SCHEDULED:
                matches_data['scheduled'].append(match)
            elif match.status == MatchStatus.LIVE:
                matches_data['live'].append(match)
            elif match.status == MatchStatus.FINISHED:
                matches_data['finished'].append(match)
        matches_data['scheduled'].sort(key=lambda x: x.date)
        matches_data['live'].sort(key=lambda x: x.date, reverse=True)
        matches_data['finished'].sort(key=lambda x: x.date, reverse=True)
        return matches_data

    def paginate_matches(self, matches_list, page_param):
        """Paginate a list of matches"""
        page = self.request.GET.get(page_param, 1)
        paginator = Paginator(matches_list, self.paginate_by)
        try:
            paginated_matches = paginator.page(page)
        except PageNotAnInteger:
            paginated_matches = paginator.page(1)
        except EmptyPage:
            paginated_matches = paginator.page(paginator.num_pages)
        return paginated_matches

    def get_match_days(self):
        """Get available match days for the filter dropdown"""
        cache_key = 'available_match_days'
        match_days = cache.get(cache_key)
        if not match_days:
            match_days = Match.objects.filter(
                season__is_active=True
            ).values_list('match_day', flat=True).distinct().order_by('match_day')
            match_days = [day for day in match_days if day is not None]
            cache.set(cache_key, match_days, 300)
        return match_days

    def get_active_teams(self):
        """Get teams that are active in the current season"""
        cache_key = 'active_teams_current_season'
        teams = cache.get(cache_key)
        if not teams:
            teams = Team.objects.filter(
                teamseasonparticipation_set__is_active=True,
                teamseasonparticipation_set__league__is_active=True
            ).distinct().order_by('name')
            cache.set(cache_key, teams, 300)
        return teams

    def get_active_leagues(self):
        """Get active leagues for filtering"""
        cache_key = 'active_leagues'
        leagues = cache.get(cache_key)
        if not leagues:
            leagues = League.objects.filter(is_active=True).order_by('-year', 'session')
            cache.set(cache_key, leagues, 600)
        return leagues

    def get_context_data(self, **kwargs):
        context = {}
        filtered_queryset = self.get_filtered_queryset()
        matches_by_status = self.get_matches_by_status(filtered_queryset)
        context['upcoming_matches'] = self.paginate_matches(
            matches_by_status['scheduled'], 'scheduled_page'
        )
        context['finished_matches'] = self.paginate_matches(
            matches_by_status['finished'], 'finished_page'
        )
        context['teams'] = self.get_active_teams()
        context['leagues'] = self.get_active_leagues()
        context['status_choices'] = MatchStatus.choices
        context['current_team_search'] = self.request.GET.get('team_search', '')
        context['current_match_day'] = self.request.GET.get('match_day', '')
        context['current_league'] = self.request.GET.get('league', '')
        context['match_days'] = self.get_match_days()
        context['match_stats'] = {
            'total_scheduled': len(matches_by_status['scheduled']),
            'total_live': len(matches_by_status['live']),
            'total_finished': len(matches_by_status['finished']),
            'total_matches': len(filtered_queryset),
        }
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['league/match_list_partial.html']
        return ['league/match_list.html']

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Request') and self.request.GET.get('format') == 'json':
            return JsonResponse({
                'scheduled_count': context['match_stats']['total_scheduled'],
                'live_count': context['match_stats']['total_live'],
                'finished_count': context['match_stats']['total_finished'],
                'html': render_to_string('match_list_partial.html', context, request=self.request)
            })
        return super().render_to_response(context, **response_kwargs)
    model = Match
    template_name = 'match_list.html'
    paginate_by = 10
    context_object_name = 'matches'

    def get_queryset(self):
        """Build the base queryset with optimizations"""
        queryset = Match.objects.select_related(
            'season', 'home_team', 'away_team'
        ).prefetch_related(
            Prefetch(
                'home_team__teamseasonparticipation_set',
                queryset=TeamSeasonParticipation.objects.select_related('league'),
                to_attr='current_season_participation'
            ),
            Prefetch(
                'away_team__teamseasonparticipation_set',
                queryset=TeamSeasonParticipation.objects.select_related('league'),
                to_attr='current_season_participation'
            ),
            'playerstats_set__player'  # For match statistics
        )
        
        # Filter by active season only
        queryset = queryset.filter(season__is_active=True)
        
        return queryset

    def get_filtered_queryset(self):
        """Apply filters based on request parameters"""
        queryset = self.get_queryset()
        
        # Team search filter (matches your template's team_search field)
        team_search = self.request.GET.get('team_search', '').strip()
        if team_search:
            queryset = queryset.filter(
                Q(home_team__name__icontains=team_search) |
                Q(away_team__name__icontains=team_search)
            )

        # Match day filter
        match_day = self.request.GET.get('match_day')
        if match_day:
            try:
                match_day = int(match_day)
                queryset = queryset.filter(match_day=match_day)
            except (ValueError, TypeError):
                pass

        # League filter
        league_id = self.request.GET.get('league')
        if league_id:
            try:
                league_id = int(league_id)
                queryset = queryset.filter(season_id=league_id)
            except (ValueError, TypeError):
                pass

        return queryset

    def get_matches_by_status(self, queryset):
        """Split matches by status and add statistics"""
        matches_data = {
            'scheduled': [],
            'live': [],
            'finished': []
        }
        
        for match in queryset:
            # Add match statistics
            match.total_goals = match.home_score + match.away_score
            match.goal_difference = abs(match.home_score - match.away_score)
            
            # Categorize by status
            if match.status == MatchStatus.SCHEDULED:
                matches_data['scheduled'].append(match)
            elif match.status == MatchStatus.LIVE:
                matches_data['live'].append(match)
            elif match.status == MatchStatus.FINISHED:
                matches_data['finished'].append(match)
        
        # Sort each category
        matches_data['scheduled'].sort(key=lambda x: x.date)  # Upcoming first
        matches_data['live'].sort(key=lambda x: x.date, reverse=True)  # Most recent first
        matches_data['finished'].sort(key=lambda x: x.date, reverse=True)  # Most recent first
        
        return matches_data

    def paginate_matches(self, matches_list, page_param):
        """Paginate a list of matches"""
        page = self.request.GET.get(page_param, 1)
        paginator = Paginator(matches_list, self.paginate_by)
        
        try:
            paginated_matches = paginator.page(page)
        except PageNotAnInteger:
            paginated_matches = paginator.page(1)
        except EmptyPage:
            paginated_matches = paginator.page(paginator.num_pages)
        
        return paginated_matches

    def get_match_days(self):
        """Get available match days for the filter dropdown"""
        cache_key = 'available_match_days'
        match_days = cache.get(cache_key)
        
        if not match_days:
            match_days = Match.objects.filter(
                season__is_active=True
            ).values_list('match_day', flat=True).distinct().order_by('match_day')
            match_days = [day for day in match_days if day is not None]
            cache.set(cache_key, match_days, 300)  # Cache for 5 minutes
        
        return match_days

    def get_active_teams(self):
        """Get teams that are active in the current season"""
        cache_key = 'active_teams_current_season'
        teams = cache.get(cache_key)
        
        if not teams:
            teams = Team.objects.filter(
               is_active=True,
            ).distinct().order_by('name')
            cache.set(cache_key, teams, 300)  # Cache for 5 minutes
        
        return teams

    def get_active_leagues(self):
        """Get active leagues for filtering"""
        cache_key = 'active_leagues'
        leagues = cache.get(cache_key)
        
        if not leagues:
            leagues = League.objects.filter(is_active=True).order_by('-year', 'session')
            cache.set(cache_key, leagues, 600)  # Cache for 10 minutes
        
        return leagues

    def get_context_data(self, **kwargs):
        # Don't call super() as we're handling pagination differently
        context = {}
        
        # Get filtered matches
        filtered_queryset = self.get_filtered_queryset()
        
        # Split matches by status
        matches_by_status = self.get_matches_by_status(filtered_queryset)
        
        # For template compatibility, use upcoming_matches and finished_matches
        context['upcoming_matches'] = self.paginate_matches(
            matches_by_status['scheduled'], 'scheduled_page'
        )
        context['finished_matches'] = self.paginate_matches(
            matches_by_status['finished'], 'finished_page'
        )
        context['live_matches'] = self.paginate_matches(
            matches_by_status['live'], 'live_page'
        )
        # Add filter options
        context['teams'] = self.get_active_teams()
        context['leagues'] = self.get_active_leagues()
        context['status_choices'] = MatchStatus.choices
        
        # Template expects these filter values
        context['current_team_search'] = self.request.GET.get('team_search', '')
        context['current_match_day'] = self.request.GET.get('match_day', '')
        context['current_league'] = self.request.GET.get('league', '')
        
        # Add match days for filter dropdown
        context['match_days'] = self.get_match_days()
        
        # Add match statistics
        context['match_stats'] = {
            'total_scheduled': len(matches_by_status['scheduled']),
            'total_live': len(matches_by_status['live']),
            'total_finished': len(matches_by_status['finished']),
            'total_matches': len(filtered_queryset),
        }
        
        return context

    def get_template_names(self):
        """Return different templates for HTMX requests"""
        if self.request.headers.get('HX-Request'):
            # Return partial template for HTMX updates
            return ['matches/match_list_partial.html']
        return [self.template_name]

    def render_to_response(self, context, **response_kwargs):
        """Handle HTMX requests with JSON response if needed"""
        if self.request.headers.get('HX-Request') and self.request.GET.get('format') == 'json':
            # Return JSON response for HTMX with specific data
            return JsonResponse({
                'scheduled_count': context['match_stats']['total_scheduled'],
                'live_count': context['match_stats']['total_live'],
                'finished_count': context['match_stats']['total_finished'],
                'html': render_to_string('matches/match_list_partial.html', context, request=self.request)
            })
        
        return super().render_to_response(context, **response_kwargs)


# Match Create/Edit View
class MatchFormView(UserPassesTestMixin, CreateView, ):
    model = Match
    form_class = MatchForm
    template_name = 'match_form.html'
    success_url = reverse_lazy('match_list')

    def get_object(self, queryset=None):
        if 'match_id' in self.kwargs:
            return get_object_or_404(Match, id=self.kwargs['match_id'])
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.get_object():
            kwargs['instance'] = self.get_object()
        return kwargs

    def form_valid(self, form):
        """
        Override the handle status change and redirect to player stats editing
        """
        #Get the match instance before saving to check its old status
        old_instance = self.get_object()
        old_status = old_instance.status if old_instance else None

        #if it is a new_match
        new_match = form.save(commit=False)

        #Check if the status is transitioning to Finished
        if new_match.status == MatchStatus.FINISHED and old_status != MatchStatus.FINISHED:

            #Using transaction.atomic() to ensure all or nothing is saved
            with transaction.atomic():
                new_match.save()

                #Auto-Create PlayerStats for all players in the Lineup
                home_lineup = Lineup.objects.filter(match=new_match, team=new_match.home_team).first()
                away_lineup = Lineup.objects.filter(match=new_match, team=new_match.away_team).first()

                players_in_match = []
                if home_lineup:
                     players_in_match.extend(home_lineup.players.all())
                if away_lineup:
                    players_in_match.extend(away_lineup.players.all())

                for player in set(players_in_match): # Use set to avoid duplicates
                    PlayerStats.objects.get_or_create(match=new_match, player=player)

            messages.success(self.request, f"Match score saved. Please enter player stats for {new_match}.")
            # Redirect to the player stats editing page
            return redirect('edit_player_stats', match_id=new_match.pk)

        # If status is not changing to FINISHED, proceed as normal
        form.save()
        messages.success(self.request, "Match saved successfully.")
        return redirect(self.success_url)

    def get_template_names(self):
        if self.get_object():
            return ['match_form.html']
        return super().get_template_names()

   
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'

# Delete Match View
class DeleteMatchView(UserPassesTestMixin, DeleteView):
    model = Match
    success_url = reverse_lazy('match_list')
    template_name = 'delete_match.html'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'

# Edit Player Stats View 
@user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')
def edit_player_stats_view(request, match_id):
    match = get_object_or_404(Match.objects.select_related('home_team', 'away_team', 'season'), 
                              id=match_id) #Get match object with related teams

    # We query player stats based on the match. The previous view ensures they exist.
    queryset = PlayerStats.objects.filter(match=match).select_related('player').prefetch_related(
        Prefetch(
            'player__playerseasonparticipation_set',
            queryset=PlayerSeasonParticipation.objects.filter(
                league=match.season, is_active=True
            ).select_related('team'), # Also prefetch the team from the participation!
            to_attr='participation' 
        )
    )

    if request.method == 'POST':
        formset = PlayerStatsFormSet(request.POST, queryset=queryset, form_kwargs={'match': match})

        if formset.is_valid():
            total_goals_from_stats = 0
            for form in formset.cleaned_data:
                # formset.cleaned_data is a list of dicts
                if form: # The form could be empty if not changed
                    total_goals_from_stats += form.get('goals', 0)
            
            total_score_from_match = match.home_score + match.away_score
            if total_goals_from_stats != total_score_from_match:
                # Add a global error to the formset
                messages.error(request, f"Validation Error: The total goals from players ({total_goals_from_stats}) does not match the final score ({total_score_from_match}).")
            else:
                # All checks passed, save the stats and trigger updates
                with transaction.atomic():
                    formset.save() # This will trigger your PlayerStats post_save signal automatically
                
                messages.success(request, "Player stats have been updated successfully!")
                return redirect('match_list')
    else: #Get Request

        formset = PlayerStatsFormSet(queryset=queryset, form_kwargs={'match': match})

    context = {
        'formset': formset,
        'match': match,
    }
    return render(request, 'edit_player_stats.html', context)


def player_profile(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    season_participations = PlayerSeasonParticipation.objects.filter(player=player).select_related('team', 'league').order_by('-league__year', '-league__session')
    
    context = {
        'player': player,
        'season_participations': season_participations,
    }
    return render(request, 'league/player_profile.html', context)



def match_details(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    home_lineup = Lineup.objects.filter(match=match, team=match.home_team).first()
    away_lineup = Lineup.objects.filter(match=match, team=match.away_team).first()
    events = match.events.all().select_related('player')

    if request.method == 'POST':
        form = MatchEventForm(request.POST, match=match)
        if form.is_valid():
            event = form.save(commit=False)
            event.match = match
            if match.status == 'LIV':
                event.minute = match.get_current_minute()
            else:
                # Handle cases where match is not live, maybe default to 0 or prompt for it
                event.minute = 0 # Or some other default
            event.save()
            return redirect('match_details', match_id=match.id)
    else:
        form = MatchEventForm(match=match)

    context = {
        'match': match,
        'home_lineup': home_lineup,
        'away_lineup': away_lineup,
        'events': events,
        'form': form,
    }

    return render(request, 'match_details.html', context)

############# Lineup Manager Begins ###############
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse
import json

def manage_lineup_view(request, match_id):
    """
    View to create or edit lineups for a specific match.
    Refactored for better performance and maintainability.
    """
    # Fetch match with related data in one query
    match = get_object_or_404(
        Match.objects.select_related('home_team', 'away_team', 'season'),
        pk=match_id
    )
    user = request.user

    # --- Permission Checks ---
    permissions = check_user_permissions(user, match)
    
    if not any(permissions.values()):
        raise PermissionDenied("You do not have permission to manage this lineup.")

    # --- POST Request Logic (Save Lineup) ---
    if request.method == 'POST':
        return handle_lineup_save(request, match, permissions)

    # --- GET Request Logic (Display Lineup Manager) ---
    context = build_lineup_context(match, permissions)
    return render(request, 'lineup_manager.html', context)


def check_user_permissions(user, match):
    """
    Check if user has permission to edit home/away team lineups.
    Returns dict with permission flags.
    """
    is_admin = user.is_staff and getattr(user, 'role', None) == 'admin'
    is_home_coach = False
    is_away_coach = False

    # Check coach permissions
    if hasattr(user, 'userprofile') and hasattr(user.userprofile, 'coach'):
        coach = user.userprofile.coach
        if coach:
            is_home_coach = CoachSeasonParticipation.objects.filter(
                coach=coach,
                team=match.home_team,
                league=match.season
            ).exists()
            
            is_away_coach = CoachSeasonParticipation.objects.filter(
                coach=coach,
                team=match.away_team,
                league=match.season
            ).exists()

    return {
        'is_admin': is_admin,
        'is_home_coach': is_home_coach,
        'is_away_coach': is_away_coach,
        'can_edit_home': is_admin or is_home_coach,
        'can_edit_away': is_admin or is_away_coach,
    }


def handle_lineup_save(request, match, permissions):
    """
    Handle POST request to save lineup data.
    """
    try:
        data = json.loads(request.body)
        team_id = int(data.get('team_id'))
        
        # Validate team_id belongs to this match
        if team_id not in [match.home_team.id, match.away_team.id]:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid team for this match.'
            }, status=400)
        
        # Check authorization for this specific team
        is_home_team = team_id == match.home_team.id
        can_edit = permissions['can_edit_home'] if is_home_team else permissions['can_edit_away']
        
        if not can_edit:
            return JsonResponse({
                'status': 'error',
                'message': 'You are not authorized to modify this team\'s lineup.'
            }, status=403)

        # Extract lineup data
        starter_ids = data.get('starters', [])
        substitute_ids = data.get('substitutes', [])
        formation = data.get('formation', '4-4-2')

        # Validate formation
        if not validate_formation(formation):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid formation format.'
            }, status=400)

        # Validate player counts
        if len(starter_ids) != 11:
            return JsonResponse({
                'status': 'error',
                'message': f'Starting lineup must have exactly 11 players (you have {len(starter_ids)}).'
            }, status=400)
        
        if len(substitute_ids) > 12:
            return JsonResponse({
                'status': 'error',
                'message': f'Maximum 12 substitutes allowed (you have {len(substitute_ids)}).'
            }, status=400)

        # Check for duplicate players
        all_player_ids = starter_ids + substitute_ids
        if len(all_player_ids) != len(set(all_player_ids)):
            return JsonResponse({
                'status': 'error',
                'message': 'A player cannot appear multiple times in the lineup.'
            }, status=400)

        # Verify all players belong to the team and are eligible
        team = match.home_team if is_home_team else match.away_team
        eligible_player_ids = set(
            PlayerSeasonParticipation.objects.filter(
                team=team,
                league=match.season,
                is_active=True
            ).values_list('player_id', flat=True)
        )

        invalid_players = set(all_player_ids) - eligible_player_ids
        if invalid_players:
            return JsonResponse({
                'status': 'error',
                'message': f'Some players are not eligible for this team: {invalid_players}'
            }, status=400)

        # Save the lineup
        lineup, created = Lineup.objects.get_or_create(team=team, match=match)

        with transaction.atomic():
            # Clear existing lineup players
            lineup.lineupplayer_set.all().delete()

            # Bulk create new lineup players
            lineup_players = []
            
            for player_id in starter_ids:
                lineup_players.append(
                    LineupPlayer(
                        lineup=lineup,
                        player_id=player_id,
                        is_starter=True
                    )
                )
            
            for player_id in substitute_ids:
                lineup_players.append(
                    LineupPlayer(
                        lineup=lineup,
                        player_id=player_id,
                        is_starter=False
                    )
                )
            
            LineupPlayer.objects.bulk_create(lineup_players)

            # Update formation
            lineup.formation = formation
            lineup.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Lineup saved successfully!',
            'data': {
                'lineup_id': lineup.id,
                'starters_count': len(starter_ids),
                'substitutes_count': len(substitute_ids),
                'formation': formation
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data.'
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Invalid data format: {str(e)}'
        }, status=400)
    except Exception as e:
        # Log the exception in production
        print(f"Unexpected error in lineup save: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred. Please try again.'
        }, status=500)


def validate_formation(formation):
    """
    Validate formation string format and ensure it adds up to 10 outfield players.
    """
    valid_formations = ['4-4-2', '4-3-3', '3-5-2', '4-2-3-1', '5-3-2', '3-4-3', '4-5-1', '5-4-1']
    return formation in valid_formations

def build_lineup_context(match, permissions):
    """
    Build context data for GET request (display lineup manager).
    """
    formations = ['4-4-2', '4-3-3', '3-5-2', '4-2-3-1', '5-3-2', '3-4-3', '4-5-1', '5-4-1']
    
    home_team_context = get_team_lineup_context(match.home_team, match, permissions['can_edit_home'])
    away_team_context = get_team_lineup_context(match.away_team, match, permissions['can_edit_away'])

    context = {
        'match': match,
        'home_team_context': home_team_context,
        'away_team_context': away_team_context,
        'formations': formations,  
        'save_lineup_url': reverse('manage_lineup', kwargs={'match_id': match.id}),
        'can_edit_home': permissions['can_edit_home'],
        'can_edit_away': permissions['can_edit_away'],
    }
    
    return context

def get_team_lineup_context(team, match, can_edit=False):
    """
    Get lineup data for a specific team.
    """
    lineup, _ = Lineup.objects.get_or_create(team=team, match=match)
    
    lineup_players = (
        LineupPlayer.objects
        .filter(lineup=lineup)
        .select_related('player')
        .order_by('-is_starter', 'player__last_name')
    )
    
    starters, substitutes, lineup_player_ids = [], [], set()
    for lp in lineup_players:
        player_data = serialize_player(lp.player)
        lineup_player_ids.add(lp.player.id)
        if lp.is_starter:
            starters.append(player_data)
        else:
            substitutes.append(player_data)
            
    eligible_players = (
        PlayerSeasonParticipation.objects
        .filter(team=team, league=match.season, is_active=True)
        .select_related('player')
        .order_by('player__last_name')
    )
    
    available_players = [
        serialize_player(psp.player)
        for psp in eligible_players
        if psp.player.id not in lineup_player_ids
    ]

    # Return Python dict, NOT JSON string
    js_payload = {
        'teamId': team.id,
        'teamName': team.name,
        'teamType': 'home' if team == match.home_team else 'away',
        'canEdit': can_edit,
        'formation': lineup.formation or '4-4-2',
        'starters': starters,
        'substitutes': substitutes,
        'availablePlayers': available_players,  # camelCase
    }

    return {
        'team': team,
        'lineup': lineup,
        'js_data': js_payload  # ← Python dict, not JSON string
    }


def serialize_player(player):
    """
    Serialize player data for JavaScript consumption.
    """
    return {
        'id': player.id,
        'first_name': player.first_name,
        'last_name': player.last_name,
        'full_name': f"{player.first_name} {player.last_name}",
        'position': getattr(player, 'position', 'N/A'),
        'jersey_number': getattr(player, 'jersey_number', ''),
    }
   