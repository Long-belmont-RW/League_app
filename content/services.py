from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Invitation
from league.models import Team
from users.models import User

@transaction.atomic
def process_invitation(request, email, role, team_id=None):
    """
    Processes an invitation by checking for existing users and invitations,
    creating a new invitation, and sending an invitation email.
    This process is atomic to prevent race conditions.
    """
    normalized_email = (email or "").strip().lower()

    if User.objects.filter(email=normalized_email).exists():
        messages.error(request, 'A user with this email already exists.')
        return False

 
    # Calculate the expiry threshold (e.g., 3 days ago)
    # Prune expired invitations for this email
    Invitation.objects.filter(email=normalized_email, expires_at__lt=timezone.now()).delete()
    
    # Check for an existing *active* invitation.
    if Invitation.objects.filter(email=normalized_email, is_accepted=False, expires_at__gt=timezone.now()).exists():
        messages.warning(request, 'An active invitation has already been sent to this email.')
        return False

    # Enforce team for both coach and player roles in this project
    team = get_object_or_404(Team, pk=team_id)

    try:
        invitation = Invitation.objects.create(
            email=normalized_email,
            team=team,
            role=role,
            sent_by=request.user
        )
    except IntegrityError:
        messages.warning(request, 'An invitation is already in progress. Please try again later.')
        return False

    # ... (rest of the function is the same) ...
    
    invite_link = request.build_absolute_uri(
        reverse('accept_invitation', args=[invitation.token])
    )
    context = {
        'invite_link': invite_link,
        'role': role.capitalize(),
        'team_name': team.name,
    }
    # Use standalone email templates
    template_name = 'coach_invite.html' if role == 'coach' else 'player_invite.html'
    html_message = render_to_string(template_name, context)
    plain_message = (
        f"You have been invited to join {context['team_name']} as a {context['role']}. "
        f"Please use the following link to accept: {invite_link}"
    )

    send_mail(
        'You have been invited to join the AUN League',
        plain_message,
        'from@example.com',
        [email],
        fail_silently=False,
        html_message=html_message
    )

    messages.success(request, 'Invitation sent successfully.')
    return True