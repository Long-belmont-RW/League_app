# league/views.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db import transaction
from django.db.models import Sum, Q, F, Prefetch
from .models import League, Lineup, Team, Match, Player, PlayerSeasonParticipation, PlayerStats, MatchStatus, \
    TeamSeasonParticipation, CoachSeasonParticipation
from .forms import MatchForm, PlayerStatsForm, PlayerStatsFormSet, LineupForm
from .utils import get_league_standings
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

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


#The improvise view for managing lineups
def manage_lineup_view(request, match_id):
    #Get the match object and user
    match = get_object_or_404(Match, pk=match_id)
    user = request.user

    # --- Permission Checks 
    is_admin = user.is_staff and user.role == 'admin'
    is_home_coach = False
    is_away_coach = False

    # Check for coach role based on your UserProfile model
    if hasattr(user, 'userprofile') and user.userprofile.coach:
        coach_profile = user.userprofile.coach

        if CoachSeasonParticipation.objects.filter(coach=coach_profile, team=match.home_team, league=match.season).exists():
            is_home_coach = True
        if CoachSeasonParticipation.objects.filter(coach=coach_profile, team=match.away_team, league=match.season).exists():
            is_away_coach = True
        
    # Deny access if the user has no permissions for this page
    if not (is_admin or is_home_coach or is_away_coach):
        raise PermissionDenied("You do not have permission to manage this lineup.")


    # --- Form & Instance Setup ---
    home_lineup, _ = Lineup.objects.get_or_create(match=match, team=match.home_team)
    away_lineup, _ = Lineup.objects.get_or_create(match=match, team=match.away_team)

    home_form = None
    away_form = None

    # ---Post request---
    if request.method == 'POST':
        #Admin or homecoach submitting the home lineup
        if 'submit_home_lineup' in request.POST and (is_admin or is_home_coach):
            form = LineupForm(request.POST, instance=home_lineup)
            if form.is_valid():
                form.save()
                messages.success(request, f"{match.home_team}'s lineup has been updated.")
                return redirect('manage_lineup', match_id=match_id)
            
        # Admin or away coach submitting the away lineup
        elif 'submit_away_lineup' in request.POST and (is_admin or is_away_coach):
            form = LineupForm(request.POST, instance=away_lineup)
            if form.is_valid():
                form.save()
                messages.success(request, f"{match.away_team}'s lineup has been updated.")
                return redirect('manage_lineup', match_id=match_id)

    # --- GET Logic (or after a failed POST) ---
    if is_admin or is_home_coach:
        home_form = LineupForm(instance=home_lineup)
    
    if is_admin or is_away_coach:
        away_form = LineupForm(instance=away_lineup)

    context = {
        'match': match,
        'home_form': home_form,
        'away_form': away_form,
    }
    return render(request, 'manage_lineup.html', context)