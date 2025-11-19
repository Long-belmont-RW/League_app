from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, F
from django.db import transaction
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

from .utils import get_season_progress, get_team_season_progress, get_win_ratio, get_matches_completed
from .forms import UserRegistrationForm, EmailAuthenticationForm, InvitationRegistrationForm, CustomUserCreationForm, UserAccountForm, UserProfileForm, PlayerCreationForm, PlayerBulkUploadForm
from django.contrib.auth.forms import PasswordChangeForm
from content.models import Invitation
import logging
import os
import random
import string

from django.contrib.auth.views import PasswordChangeView, PasswordResetConfirmView
from django.urls import reverse_lazy, reverse
from django.core.mail import send_mail

# Helper function to get dashboard URL based on user role
def get_dashboard_url(user):
    if user.role == 'admin':
        return reverse('admin_dashboard')
    elif user.role == 'coach':
        return reverse('coach_dashboard')
    elif user.role == 'player':
        return reverse('player_dashboard')
    elif user.role == 'fan':
        return reverse('fan_dashboard')
    return reverse('home') # Default fallback
from .services.bulk_upload import import_players_csv_for_team



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

    #Component Data
    all_users = User.objects.order_by('-date_joined')[:10]
    all_coaches = Coach.objects.all()[:10]
    all_players = Player.objects.all()[:10]

    #Numerics
    user_count = User.objects.all().count()
    coach_count = Coach.objects.all().count()
    player_count = Player.objects.all().count()

    # Get the season progress
    season_progress = get_season_progress()

    #Get the matches completed
    matches_completed = get_matches_completed()

    #Get the latest match
    latest_match = Match.objects.order_by('-date').first()



    # Check if the user is an admin
    # Redirect if not an admin
    if request.user.role != 'admin' or request.user.is_superuser == False:
        logger.warning(f"Unauthorized access attempt by user: {request.user.username}")
        messages.error(request, "Only admins can access this page.")
        return redirect('login')
    
    profile = UserProfile.objects.filter(user=request.user).first()
    context = {
        'profile': profile,
        'all_users': all_users,
        'all_coaches': all_coaches,
        'all_players': all_players,
        'season_progress': season_progress,
        'latest_match': latest_match,
        'matches_completed':matches_completed,
        'user_count':user_count,
        'player_count':player_count,
        'coach_count':coach_count,
       
    }

    return render(request, 'admin_dashboard.html', context)


@user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')
def bulk_upload_players_view(request):
    # Match admin check behavior with admin_dashboard_view
    if request.user.role != 'admin' or request.user.is_superuser is False:
        messages.error(request, "Only admins can access this page.")
        return redirect('login')

    if request.method == 'POST':
        form = PlayerBulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            result = import_players_csv_for_team(
                form.cleaned_data['team'],
                form.cleaned_data['league'],
                form.cleaned_data['file'],
            )
            if result.errors:
                for e in result.errors[:200]:
                    messages.error(request, e)
            else:
                messages.success(
                    request,
                    f"Users created: {result.created_users}, attached: {result.existing_attached}, emails sent: {result.emails_sent}."
                )
                return redirect('admin_dashboard')
    else:
        form = PlayerBulkUploadForm()

    return render(request, 'bulk_upload_players.html', { 'form': form })


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
    

    #Tracking Stats
    season_progress = get_season_progress()
    team_progress = get_team_season_progress(team=coach_team.team)
    win_ratio = get_win_ratio(team=coach_team.team)


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
        'season_progress':season_progress,
        'team_progress':team_progress,
        'win_ratio':win_ratio,
     
    }

    logger.info(f"Rendering image Url: {coach_profile.image.url if coach_profile.image else 'No image available'}")

    return render(request, 'coach_dashboard.html', context)



#Work needs to be done here....DON'T FORGET
@user_passes_test(lambda u: u.is_authenticated and u.role == 'player')
def player_dashboard_view(request):
    if request.user.role != 'player':
        messages.error(request, "Only players can access this page.")
        return redirect('login')

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
            redirect('home')
            logger.error(f"Player team not found for user: {request.user.username}")
            messages.error(request, "Player team not found.")


    else:
        messages.error(request,'No active leagues yet...contact admin')
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

    # Ensure fan has a profile
    fan_profile = UserProfile.objects.filter(user=request.user).first()
    if not fan_profile:
        logger.error(f"Fan profile not found for user: {request.user.username}")
        messages.error(request, "Fan profile not found.")
        return redirect('login')

    # Build dashboard context via service layer
    try:
        from users.services.fan_dashboard import build_fan_dashboard_context
        context = build_fan_dashboard_context(request.user)
    except Exception as e:
        logger.exception("Error building fan dashboard context: %s", e)
        messages.error(request, "There was an error loading your dashboard. Please try again.")
        context = {
            'fan_profile': fan_profile,
            'latest_league': None,
            'matches': [],
            'teams': [],
            'top_goal_scorer': None,
            'top_assist_provider': None,
            'top_team': None,
            'top_clean_sheet': None,
            'top_player': None,
            'live_match': None,
            'live_match_events': [],
            'upcoming_matches': [],
            'recent_results': [],
            'standings_top': [],
            'top_scorers': [],
            'top_assists': [],
            'top_clean_sheets': [],
            'favorite_teams': [],
            'favorite_team_cards': [],
            'notifications': [],
        }

    return render(request, 'fan_dashboard.html', context)





@login_required
@user_passes_test(lambda u: u.role == 'admin')
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
def profile_edit_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    password_form = PasswordChangeForm(user, request.POST if 'change_password' in request.POST else None)
    
    if request.method == 'POST':
        if 'change_password' in request.POST:
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, 'Your password was successfully updated!')
                return redirect(get_dashboard_url(request.user))
            else:
                messages.error(request, 'Please correct the password change errors below.')
        
        account_form = UserAccountForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if account_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                account_form.save()
                profile_instance = profile_form.save(commit=False)
                
                remove_image_checked = request.POST.get('remove_image')
                new_image_uploaded = 'image' in request.FILES

                if remove_image_checked and not new_image_uploaded:
                    if profile_instance.image:
                        profile_instance.image.delete(save=False)
                    profile_instance.image = None
                
                profile_instance.save()
                profile_form.save_m2m()

            messages.success(request, 'Profile updated successfully.')
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url or get_dashboard_url(request.user))
        else:
            # Only show profile form errors if it's not a password change attempt
            if 'change_password' not in request.POST:
                messages.error(request, 'Please correct the profile errors below.')

    else:
        account_form = UserAccountForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'account_form': account_form if 'account_form' in locals() else UserAccountForm(instance=user),
        'profile_form': profile_form if 'profile_form' in locals() else UserProfileForm(instance=profile),
        'password_form': password_form,
        'next': request.GET.get('next', ''),
    }
    return render(request, 'profile_edit.html', context)



class CustomPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy('profile_edit')

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    success_url = reverse_lazy('login')
    template_name = 'registration/password_reset_confirm.html'

@login_required
def add_player_view(request):
    if request.user.role != 'coach':
        messages.error(request, "Only coaches can add players.")
        return redirect('home')

    if request.method == 'POST':
        form = PlayerCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user object but don't save to DB yet
                    user = form.save(commit=False)
                    user.role = 'player'
                    user.username = form.cleaned_data['email'].split('@')[0]
                    
                    # Generate a random password
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                    user.set_password(password)
                    
                    # Save the user. This will trigger the signal.
                    user.save()
                    
                    # The signal has created a Player object. Now update its position.
                    player = user.userprofile.player
                    player.position = form.cleaned_data['position']
                    player.save()
                    
                    # Get coach's current team
                    coach_profile = request.user.userprofile
                    latest_league = League.objects.latest('created_at')
                    coach_participation = CoachSeasonParticipation.objects.get(coach=coach_profile.coach, league=latest_league)
                    team = coach_participation.team
                    
                    # Add player to the team for the current season
                    PlayerSeasonParticipation.objects.create(
                        player=player,
                        team=team,
                        league=latest_league
                    )
                    
                    # For development, print the password. In production, you'd email it.
                    # print(f"Generated password for {user.email}: {password}")
                    
                    # Send email with login details
                    subject = 'Your League App Account Details'
                    message = f'Hello {user.first_name},\n\nYour account for the League App has been created.\nYour email: {user.email}\nYour temporary password: {password}\n\nPlease log in and change your password as soon as possible.'
                    from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'leagueaun@gmail.com') # Use environment variable or default
                    recipient_list = [user.email]
                    
                    try:
                        send_mail(subject, message, from_email, recipient_list)
                        messages.success(request, f"Player {user.first_name} {user.last_name} has been created and added to your team. An email with login details has been sent to {user.email}.")
                    except Exception as mail_e:
                        logger.error(f"Failed to send email to {user.email}: {mail_e}")
                        messages.warning(request, f"Player {user.first_name} {user.last_name} has been created and added to your team, but failed to send login details email. Please inform the player manually. Temporary password: {password}")

                return redirect('coach_dashboard')
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")

    else:
        form = PlayerCreationForm()

    return render(request, 'add_player.html', {'form': form})

def coming_soon(request):
    return render(request, 'coming_soon.html')