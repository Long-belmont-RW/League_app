from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta # <-- Make sure timedelta is imported
from django.contrib import messages
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Invitation, Team, User

@transaction.atomic
def process_invitation(request, email, role, team_id=None):
    """
    Processes an invitation by checking for existing users and invitations,
    creating a new invitation, and sending an invitation email.
    This process is atomic to prevent race conditions.
    """
    if User.objects.filter(email=email).exists():
        messages.error(request, 'A user with this email already exists.')
        return False

 
    # Calculate the expiry threshold (e.g., 3 days ago)
    expiry_threshold = timezone.now() - timedelta(days=3)
    # Delete invitations that were created before the threshold
    Invitation.objects.filter(email=email, created_at__lt=expiry_threshold).delete()
    
    # Check for an existing *active* invitation.
    if Invitation.objects.filter(email=email, is_accepted=False).exists():
        messages.warning(request, 'An active invitation has already been sent to this email.')
        return False

    team = get_object_or_404(Team, pk=team_id) if team_id else None

    invitation = Invitation.objects.create(
        email=email,
        team=team,
        role=role,
        sent_by=request.user
    )

    # ... (rest of the function is the same) ...
    
    invite_link = request.build_absolute_uri(
        reverse('accept_invitation', args=[invitation.token])
    )
    context = {
        'invite_link': invite_link,
        'role': role.capitalize(),
        'team_name': team.name if team else "the league"
    }
    html_message = render_to_string('generic_invite.html', context)
    plain_message = f"You have been invited to join {context['team_name']} as a {context['role']}. Please use the following link to accept: {invite_link}"

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