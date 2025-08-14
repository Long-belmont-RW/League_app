from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from .models import Invitation
from users.models import UserProfile
from .forms import CoachInvitationForm, PlayerInvitationForm
from .services import process_invitation
from league.models import CoachSeasonParticipation, League

@login_required
@require_http_methods(["GET", "POST"])
def invite_player_view(request):
    if request.user.role != 'coach':
        messages.error(request, "Only coaches can invite players.")
        return redirect('home')

    if request.method == 'POST':
        form = PlayerInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                coach_profile = request.user.userprofile
                active_league = League.objects.filter(is_active=True).order_by('-created_at').first()
                if not active_league:
                    messages.error(request, "No active league found.")
                    return redirect('coach_dashboard')
                coach_season_participation = CoachSeasonParticipation.objects.select_related('team').get(
                    coach=coach_profile.coach,
                    league=active_league
                )
                team = coach_season_participation.team
            except (UserProfile.DoesNotExist, CoachSeasonParticipation.DoesNotExist):
                messages.error(request, "Could not determine your team. Please contact an administrator.")
                return redirect('coach_dashboard')

            process_invitation(request, email, 'player', team_id=team.id)
            return redirect('invite_player')
    else:
        form = PlayerInvitationForm()

    return render(request, 'invite_player.html', {'form': form})


@login_required
@require_http_methods(["GET", "POST"])
def invite_coach(request):
    if request.user.role != 'admin':
        messages.error(request, "Only admins can invite coaches.")
        return redirect('home')
    if request.method == 'POST':
        form = CoachInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            team = form.cleaned_data['team']
            process_invitation(request, email, 'coach', team_id=team.id)
            return redirect('invite_coach')
    else:
        form = CoachInvitationForm()
    
    return render(request, 'invite_coach.html', {'form': form})

@require_http_methods(["GET"]) 
def accept_invitation(request, token):
    try:
        invitation = Invitation.objects.get(token=token, is_accepted=False)
        if invitation.is_expired():
            messages.error(request, 'This invitation has expired.')
            return redirect('home')
    except Invitation.DoesNotExist:
        messages.error(request, 'Invalid invitation link.')
        return redirect('home')

    return redirect(reverse('register') + f'?token={token}')