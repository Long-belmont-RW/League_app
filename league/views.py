# league/views.py
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.db.models import Sum, Q, F, Prefetch
from .models import League, Lineup, Team, Match, Player, PlayerSeasonParticipation, PlayerStats, MatchStatus, TeamSeasonParticipation
from .forms import MatchForm, PlayerStatsForm, PlayerStatsFormSet, LineupForm
from .utils import get_league_standings
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.cache import cache

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
class MatchFormView(LoginRequiredMixin, CreateView):
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

    def get_template_names(self):
        if self.get_object():
            return ['match_form.html']
        return super().get_template_names()

# Delete Match View
class DeleteMatchView(LoginRequiredMixin, DeleteView):
    model = Match
    success_url = reverse_lazy('match_list')
    template_name = 'delete_match.html'

# Edit Player Stats View (HTMX-enabled)
def edit_player_stats_view(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    # Get all players for both teams in the match's league
    home_players = match.home_team.get_current_players(match.season)
    away_players = match.away_team.get_current_players(match.season)
    all_players = list(home_players) + list(away_players)
    # Ensure PlayerStats exist for all players in this match
    for player in all_players:
        PlayerStats.objects.get_or_create(match=match, player=player)
    # Now get all PlayerStats for this match
    formset = PlayerStatsFormSet(
        queryset=PlayerStats.objects.filter(match=match),
        form_kwargs={'match': match}
    )
    if request.method == 'POST':
        formset = PlayerStatsFormSet(request.POST, form_kwargs={'match': match})
        if formset.is_valid():
            for form in formset:
                if form.has_changed():
                    stat = form.save(commit=False)
                    stat.match = match
                    stat.save()
                redirect_url = reverse_lazy('match_list')
                return redirect(redirect_url,)
        #     html = render_to_string('league/partials/player_stats_formset.html', {
        #         'formset': formset, 'match': match
        #     }, request=request)
        #     return HttpResponse(html)
        # html = render_to_string('partials/player_stats_formset.html', {
        #     'formset': formset, 'match': match
        # }, request=request)
        # return HttpResponse(html)
    html = render_to_string('edit_player_stats.html', {
        'formset': formset, 'match': match
    }, request=request)

    return HttpResponse(html)

# Lineup Create View
class LineupCreateView(LoginRequiredMixin, CreateView):
    model = Lineup
    form_class = LineupForm
    template_name = 'lineup_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['match'] = Match.objects.get(id=self.kwargs['match_id'])
        return kwargs

    def form_valid(self, form):
        form.instance.match = Match.objects.get(id=self.kwargs['match_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('match_list')