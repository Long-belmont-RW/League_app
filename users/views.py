from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, F
from .models import UserProfile, User
from league.models import (
    Coach,
    Player,
    Match,
    PlayerSeasonParticipation,
    League,
    MatchStatus,
    CoachSeasonParticipation,
    TeamSeasonParticipation,
    PlayerStats,
    Lineup,
)
from django.utils import timezone

from .utils import get_season_progress
from .forms import UserRegistrationForm, EmailAuthenticationForm, InvitationRegistrationForm, CustomUserCreationForm
from content.models import Invitation
import logging

#set up logging
logger = logging.getLogger(__name__)

# Login view
def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('username')  # username field contains email
            password = form.cleaned_data.get('password')
            user = authenticate(username=email, password=password)

            if user is not None:
                login(request, user)

                # Get the 'next' parameter if it exists
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                # Default redirect after successful login
                return redirect('home')  
            else:
                messages.error(request, "Invalid email or password")
        else: 
            messages.error(request, "Invalid email or password")
    else:
        form = EmailAuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

def register_view(request):
    token = request.GET.get('token')
    invitation = None
    if token:
        try:
            invitation = Invitation.objects.get(token=token, is_accepted=False)
            if invitation.is_expired():
                messages.error(request, 'This invitation has expired.')
                return redirect('home')
        except Invitation.DoesNotExist:
            messages.error(request, 'Invalid invitation link.')
            return redirect('home')

    form_class = InvitationRegistrationForm if invitation else UserRegistrationForm

    if request.method == 'POST':
        if invitation:
            form = form_class(request.POST)
        else:
            form = form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if invitation:
                user.email = invitation.email
                user.role = invitation.role
            user.save() # The signal will now create the UserProfile and Player/Coach object

            if invitation:
                team = invitation.team
                latest_league = League.objects.latest('created_at')
                user_profile = UserProfile.objects.get(user=user)

                if user.role == 'player':
                    PlayerSeasonParticipation.objects.create(player=user_profile.player, team=team, league=latest_league)
                elif user.role == 'coach':
                    CoachSeasonParticipation.objects.create(coach=user_profile.coach, team=team, league=latest_league)
                
                invitation.is_accepted = True
                invitation.save()

            login(request, user, backend='users.authentication.EmailRoleAuthBackend')
            messages.success(request, f"Account created for {user.username}!")
            
            if invitation:
                if invitation.role == 'coach':
                    return redirect('coach_dashboard')
                elif invitation.role == 'player':
                    return redirect('player_dashboard')
            
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial_data = {}
        if invitation:
            initial_data['email'] = invitation.email
            form = InvitationRegistrationForm(initial=initial_data)
            form.fields['email'].widget.attrs['readonly'] = True
        else:
            form = UserRegistrationForm()


    return render(request, 'registration/register.html', {'form': form, 'invitation': invitation})

@user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')
def admin_dashboard_view(request): 
    all_users = User.objects.all()[:10]
    all_coaches = Coach.objects.all()[:10]
    all_players = Player.objects.all()[:10]

    # Get the season progress
    season_progress = get_season_progress()

    #Get the latest match
    latest_match = Match.objects.order_by('-date').first()

    # Check if the user is an admin
    # Redirect if not an admin
    if request.user.role != 'admin' or request.user.is_superuser == False:
        logger.warning(f"Unauthorized access attempt by user: {request.user.username}")
        messages.error(request, "Only admins can access this page.")
        return redirect('login')
    
    profile = UserProfile.objects.filter(user=request.user)
    context = {
        'profile': profile,
        'all_users': all_users,
        'all_coaches': all_coaches,
        'all_players': all_players,
        'season_progress': season_progress,
        'latest_match': latest_match
    }

    return render(request, 'admin_dashboard.html', context)


@user_passes_test(lambda u: u.is_authenticated and u.role == 'coach')
def coach_dashboard_view(request):
    if request.user.role != 'coach':
        messages.error(request, "Only coaches can access this page.")
        return redirect('login')

    #Get the coach profile
    coach_profile = UserProfile.objects.filter(user=request.user).first()
    logger.info(f"Coach profile: {coach_profile.user if coach_profile else 'None'}")
    logger.info(f"Profile coach: {coach_profile.coach if coach_profile and coach_profile.coach else 'None'}")
    if not coach_profile or not coach_profile.coach:
        logger.error(f"Coach profile not found for user: {request.user.username}")
        messages.error(request, "Coach profile not found.")

    #Get the latest league
    latest_league = League.objects.order_by('-created_at').first()

    #Get the coach's team
    coach_team = CoachSeasonParticipation.objects.filter(coach=coach_profile.coach, league=latest_league).first()
    logger.info(f"Coach team: {coach_team.team.name if coach_team else 'None'}")

    #Get the coach team season participation object
    if not coach_team:
        logger.error(f"Coach team not found for user: {request.user.username}")
        messages.error(request, "Coach team not found.")
        return redirect('login')
    else:
        team_stats = TeamSeasonParticipation.objects.filter(team=coach_team.team, league=latest_league).first()
        logger.info(f"Team stats: {team_stats} for team {coach_team.team.name if coach_team.team else 'None'} in league {latest_league.year if latest_league else 'None'}")

    #Get all teams the coach has coached
    all_teams = CoachSeasonParticipation.objects.filter(coach=coach_profile.coach).values_list('team__name', flat=True)
    logger.info(f"All teams for coach {coach_profile.user.username}: {list(all_teams)}")

    # --- New/Modified Query for Upcoming Matches ---
    now = timezone.now()  # Get the current time in the active timezone     
    upcoming_matches = Match.objects.filter(
        Q(home_team=coach_team.team) | Q(away_team=coach_team.team), season=latest_league, status=MatchStatus.SCHEDULED)
    logger.info(f"Upcoming matches for coach {coach_profile.user.username}: {upcoming_matches.count()} matches found")


    #Get all completed matches for the coach's team
    completed_matches = Match.objects.filter(
        Q(home_team=coach_team.team) | Q(away_team=coach_team.team), season=latest_league, status=MatchStatus.FINISHED)
    # Get the latest *completed* match for the coach
    latest_completed_match = completed_matches.order_by('-date').first()
    logger.debug(f"Latest completed match for coach {coach_profile.user.username}: {latest_completed_match.id if latest_completed_match else 'None'}")

    #Get all matches won by the coach's team
    wins = completed_matches.filter(
        Q(home_team=coach_team.team, home_score__gt=F('away_score')) |
        Q(away_team=coach_team.team, away_score__gt=F('home_score'))
    )
    logger.info(f"Total wins for coach {coach_profile.user.username}: {wins.count()}")

    #Get all matches lost by the coach's team
    losses = completed_matches.filter(
        Q(home_team=coach_team.team, home_score__lt=F('away_score')) |
        Q(away_team=coach_team.team, away_score__lt=F('home_score'))
    )
    logger.info(f"Total losses for coach {coach_profile.user.username}: {losses.count()}")

    #Get all matches drawn by the coach's team
    draws = completed_matches.filter(
        Q(home_team=coach_team.team, home_score=F('away_score')) |
        Q(away_team=coach_team.team, away_score=F('home_score'))
    )
    logger.info(f"Total draws for coach {coach_profile.user.username}: {draws.count()}")



    # Get the latest match for the coach
    latest_match = upcoming_matches.first()
    logger.info(f"Latest match for coach {coach_profile.user.username}: {latest_match.id if latest_match else 'None'}")
    if not latest_match:
        logger.error(f"No matches found for coach: {coach_profile.user.username}")
    
    #Get players from the coach's team
    players = PlayerSeasonParticipation.objects.filter(team=coach_team.team, league=latest_league).select_related('player')[:10]
    logger.info(f"Players coached by {coach_profile.user.username}: {[player.player.last_name for player in players]}")
    

    context = {
        'coach_profile': coach_profile,
        'coach_team': coach_team,
        'all_teams': all_teams,
        'upcoming_matches': upcoming_matches,
        'latest_completed_match': latest_completed_match,
        'latest_match': latest_match,
        'latest_league': latest_league,
        'team_stats': team_stats,
        'players': players,
        'wins': wins,
        'losses': losses,
        'draws': draws,
     
    }

    logger.info(f"Rendering image Url: {coach_profile.image.url if coach_profile.image else 'No image available'}")

    return render(request, 'coach_dashboard.html', context)




@login_required
@user_passes_test(lambda u: u.is_authenticated and u.role == 'player')
def player_dashboard_view(request):
    # if request.user.role != 'player':
    #     messages.error(request, "Only players can access this page.")
    #     return redirect('login')

    #Get the player profile
    player_profile = UserProfile.objects.filter(user=request.user).first()
    logger.info(f"Player profile: {player_profile.user if player_profile else 'None'}")
    logger.info(f"Profile player: {player_profile.player if player_profile and player_profile.player else 'None'}")
    if not player_profile or not player_profile.player:
        logger.error(f"Player profile not found for user: {request.user.username}")
        messages.error(request, "Player profile not found.")

    # Resolve active league with safe fallback
    latest_league = (
        League.objects.filter(is_active=True).order_by('-created_at').first()
        or League.objects.order_by('-created_at').first()
    )
    logger.info(f"Latest league: {latest_league.year if latest_league else 'None'}")

    if latest_league:
          # Get the player's recent team
        player_team = (
            PlayerSeasonParticipation.objects.select_related('team', 'player', 'league')
            .filter(player=player_profile.player, league=latest_league)
            .first()
        )
        logger.info(f"Player team: {player_team.team.name if player_team else 'None'}")
        
        # Check if the player has a team
        # If not, redirect to login or show an error message
        if not player_team:
            logger.error(f"Player team not found for user: {request.user.username}")
            messages.error(request, "Player team not found.")


    else:
        player_team = None
        logger.error("No leagues found in the database.")
       

    #Get all teams the player has played for
    # This will return a list of team names the player has participated in
    all_teams = PlayerSeasonParticipation.objects.filter(player=player_profile.player).values_list('team__name', flat=True)
    logger.info(f"All teams for player {player_profile.user.username}: {list(all_teams)}")

    
    


    # Upcoming matches and next match
    upcoming_matches = (
        Match.objects.filter(
            Q(home_team=player_team.team) | Q(away_team=player_team.team),
            season=latest_league,
            status=MatchStatus.SCHEDULED,
        )
        .select_related('home_team', 'away_team')
        .order_by('date')
    )

    next_match = upcoming_matches.first()
    logger.info(
        f"Next match for player {player_profile.user.username}: {getattr(next_match, 'id', None)}"
    )

    # Is player named in lineup for next match?
    is_in_lineup = False
    if next_match and player_team:
        try:
            is_in_lineup = Lineup.objects.filter(
                match=next_match, team=player_team.team, players=player_profile.player
            ).exists()
        except Exception:
            is_in_lineup = False

    # Latest completed match
    latest_completed_match = (
        Match.objects.filter(
            Q(home_team=player_team.team) | Q(away_team=player_team.team),
            season=latest_league,
            status=MatchStatus.FINISHED,
        )
        .select_related('home_team', 'away_team')
        .order_by('-date')
        .first()
    )

    # Recent contributions (last 5 matches)
    recent_stats = (
        PlayerStats.objects.filter(player=player_profile.player, match__season=latest_league)
        .select_related('match', 'match__home_team', 'match__away_team')
        .order_by('-match__date')[:5]
    )

    # Season totals from participation record
    season_totals = None
    if player_team:
        season_totals = {
            'goals': player_team.goals,
            'assists': player_team.assists,
            'yellow_cards': player_team.yellow_cards,
            'red_cards': player_team.red_cards,
            'clean_sheets': player_team.clean_sheets,
            'matches_played': player_team.matches_played,
        }

    # Mini league table
    team_table = (
        TeamSeasonParticipation.objects.filter(league=latest_league)
        .select_related('team')
        .all()
    )

    # Lightweight notifications
    notifications = []
    if next_match:
        notifications.append(
            f"Upcoming match: {next_match.home_team} vs {next_match.away_team}"
        )
        notifications.append(
            "You are in the lineup." if is_in_lineup else "You are not named in the lineup yet."
        )
    if latest_completed_match:
        notifications.append("Last result recorded. Check your contributions below.")

    
    context = {
        'player_profile': player_profile,
        'player_team': player_team,
        'all_teams': all_teams,
        'upcoming_matches': upcoming_matches,
        'next_match': next_match,
        'is_in_lineup': is_in_lineup,
        'latest_completed_match': latest_completed_match,
        'recent_stats': recent_stats,
        'season_totals': season_totals,
        'team_table': team_table,
        'latest_league': latest_league,
        'notifications': notifications,
    }


    return render(request, 'player_dashboard.html', context)


@login_required
def fan_dashboard_view(request):
    if request.user.role != 'fan':
        messages.error(request, "Only fans can access this page.")
        return redirect('login')
    logger.info(f"User {request.user.username} is accessing the fan dashboard.")
    # Get the fan profile
    fan_profile = UserProfile.objects.filter(user=request.user).first()
    logger.info(f"Fan profile: {fan_profile.user if fan_profile else 'None'}")

    if not fan_profile: 
        logger.error(f"Fan profile not found for user: {request.user.username}")
        messages.error(request, "Fan profile not found.")
        return redirect('login')
    
    # Get the latest league
    latest_league = League.objects.order_by('-created_at').first()

    

    #Get all matches in the latest league
    matches = Match.objects.filter(season=latest_league).order_by('-date')
    logger.info(f"Matches in the latest league: {matches.count()} matches found")   

    #Get live match in the latest league
    live_match = matches.filter(status=MatchStatus.LIVE).first()
    logger.info(f"Live match in the latest league: {live_match.home_team} vs {live_match.away_team}" if live_match else "No live match currently")

    #get match events for the live match
    if live_match:
        match_events = live_match.get_match_events()
        logger.info(f"Match events for live match {live_match.id}: {match_events.count()} events found")
    
    #Get all teams in the latest league
    teams = TeamSeasonParticipation.objects.filter(league=latest_league)
    logger.info(f"Teams in the latest league: {[team.team.name for team in teams]}")

    #Get top goal scorer in the lates league
    top_goal_scorer = PlayerSeasonParticipation.objects.filter(
        league=latest_league
    ).order_by('-goals').first()

    #Get top assist provider in the latest league
    top_assist_provider = PlayerSeasonParticipation.objects.filter(
        league=latest_league
    ).order_by('-assists').first()

    #Get top team in the latest league
    top_team = TeamSeasonParticipation.objects.filter(
        league=latest_league
    ).order_by('-points').first()

   
    
    # Get most clean sheet
    top_clean_sheet = PlayerSeasonParticipation.objects.filter(
        player__position='GK',  # Assuming 'GK' is the position for Goalkeeper
        league=latest_league).order_by('-clean_sheets').first()
    logger.info(f"Top clean sheet player: {top_clean_sheet.player.last_name if top_clean_sheet else 'None'}")   

    #Get top player in the lates league
    top_player = PlayerSeasonParticipation.objects.filter(
        league=latest_league
    ).order_by('-goals', '-assists').first()


    context = {
        'fan_profile': fan_profile,
        'latest_league': latest_league,
        'matches': matches,
        'teams': teams,
        'top_goal_scorer': top_goal_scorer,
        'top_assist_provider': top_assist_provider,
        'top_team': top_team,
        'top_clean_sheet': top_clean_sheet,
        'top_player': top_player,
        'live_match': live_match,
    }

    return render(request, 'fan_dashboard.html', context)






""""Future improvements:"""
# - Add email verification for new registrations
# - Implement password reset functionality
# - Add user profile management

@login_required
@user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')
def create_user_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('admin_dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'create_user.html', {'form': form})


@login_required
def complete_profile_view(request):
    if request.method == 'POST':
        form = UserProfileCompletionForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for completing your profile!')
            return redirect('home') # Or wherever you want to redirect after completion
    else:
        form = UserProfileCompletionForm(instance=request.user)

    return render(request, 'complete_profile.html', {'form': form})