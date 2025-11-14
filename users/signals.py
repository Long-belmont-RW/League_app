from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile, Notification
from league.models import Coach, CoachRoles, Player, LineupPlayer
from django.db import transaction
import logging
from django.core.mail import send_mail
from django.conf import settings


User = get_user_model()



logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile_and_linked_object(sender, instance, created, **kwargs):
    """
    Signal handler to create a UserProfile and, if the user's role is 'coach' or 'player',
    a corresponding Coach or Player object, linking them to the UserProfile.

    Args:
        sender: The model class that sent the signal (User in this case).
        instance: The actual instance of the User that was just saved.
        created: A boolean; True if a new record was created, False if an existing one was updated.
        kwargs: Additional keyword arguments.
    """
    # Use a transaction.atomic() block to ensure all operations are atomic.
    # If any part fails, the entire transaction is rolled back.
    with transaction.atomic():
        try:
            # 1. Get or Create UserProfile for the User
            user_profile, user_profile_created = UserProfile.objects.get_or_create(user=instance)

            if user_profile_created:
                logger.info(f"UserProfile created for user: {instance.username} (ID: {instance.id})")
            else:
                logger.debug(f"UserProfile already exists for user: {instance.username} (ID: {instance.id})")

            # 2. Handle Coach object creation if role is 'coach'
            if instance.role == 'coach':
                if not user_profile.coach:
                    coach_first_name = instance.first_name if instance.first_name else instance.username
                    coach_last_name = instance.last_name if instance.last_name else ''

                    coach_obj = Coach.objects.create(
                        first_name=coach_first_name,
                        last_name=coach_last_name,
                        role=CoachRoles.ASSISTANT # Default coach role
                    )
                    logger.info(f"Coach object created for user: {instance.username} (Coach ID: {coach_obj.id})")

                    user_profile.coach = coach_obj
                    user_profile.save()
                    logger.info(f"Coach object linked to UserProfile for user: {instance.username}")
                else:
                    logger.debug(f"Coach object already linked to UserProfile for user: {instance.username}")

            # 3. Handle Player object creation if role is 'player'
            elif instance.role == 'player':
                if not user_profile.player:
                    player_first_name = instance.first_name if instance.first_name else instance.username
                    player_last_name = instance.last_name if instance.last_name else ''

                    player_obj = Player.objects.create(
                        first_name=player_first_name,
                        last_name=player_last_name,
                        position='MF' # Default position
                    )
                    logger.info(f"Player object created for user: {instance.username} (Player ID: {player_obj.id})")

                    user_profile.player = player_obj
                    user_profile.save()
                    logger.info(f"Player object linked to UserProfile for user: {instance.username}")
                else:
                    logger.debug(f"Player object already linked to UserProfile for user: {instance.username}")

        except Exception as e:
            logger.error(f"Error in post_save signal for User {instance.username} (ID: {instance.id}): {e}", exc_info=True)
            raise # Re-raise to ensure the transaction is rolled back


@receiver(post_delete, sender=Coach)
def delete_user_profile_on_coach_delete(sender, instance, **kwargs):
    """
    Signal handler to delete the associated UserProfile and User when a Coach object is deleted.
    """
    with transaction.atomic():
        try:
            user_profile = UserProfile.objects.select_related('user').get(coach=instance)
            user_username = user_profile.user.username if user_profile.user else "N/A"
            logger.info(
                f"Deleting UserProfile (ID: {user_profile.id}) and User (Username: {user_username}) "
                f"due to Coach (ID: {instance.id}) deletion."
            )
            user_profile.delete()

        except UserProfile.DoesNotExist:
            logger.warning(f"No UserProfile found for deleted Coach (ID: {instance.id}). No action needed.")
        except Exception as e:
            logger.error(f"Error deleting UserProfile/User for Coach (ID: {instance.id}): {e}", exc_info=True)
            raise


@receiver(post_delete, sender=Player)
def delete_user_profile_on_player_delete(sender, instance, **kwargs):
    """
    Signal handler to delete the associated UserProfile and User when a Player object is deleted.
    """
    with transaction.atomic():
        try:
            user_profile = UserProfile.objects.select_related('user').get(player=instance)
            user_username = user_profile.user.username if user_profile.user else "N/A"
            logger.info(
                f"Deleting UserProfile (ID: {user_profile.id}) and User (Username: {user_username}) "
                f"due to Player (ID: {instance.id}) deletion."
            )
            user_profile.delete()

        except UserProfile.DoesNotExist:
            logger.warning(f"No UserProfile found for deleted Player (ID: {instance.id}). No action needed.")
        except Exception as e:
            logger.error(f"Error deleting UserProfile/User for Player (ID: {instance.id}): {e}", exc_info=True)
            raise

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

@receiver(post_save, sender=LineupPlayer)
def send_lineup_add_notification(sender, instance, created, **kwargs):
    """Send notification to player when added to a lineup."""
    if created:
        logger.debug(f"send_lineup_add_notification triggered for player {instance.player.id}")
        try:
            user = instance.player.userprofile.user
            logger.debug(f"User found for notification: {user.username}")
            match_info = f"{instance.lineup.match.home_team} vs {instance.lineup.match.away_team} on {instance.lineup.match.date.strftime('%Y-%m-%d')}"
            
            # Create in-app notification
            Notification.objects.create(
                user=user,
                title="You've been selected for a match lineup!",
                message=f"You have been selected for the match: {match_info}. Check the lineup for details.",
                match=instance.lineup.match
            )

            # Prepare email context
            context = {
                'player_name': user.first_name or user.username,
                'match': instance.lineup.match,
                'added': True,
                'match_url': settings.BASE_URL + reverse('match_details', args=[instance.lineup.match.id]),
            }
            
            # Render HTML and text versions
            html_content = render_to_string('emails/lineup_notification.html', context)
            text_content = f"Hi {context['player_name']},\n\nYou have been selected for the match: {match_info}. Please log in to view the full lineup.\n\nView the lineup: {context['match_url']}"

            # Send email
            msg = EmailMultiAlternatives(
                subject="You've Been Selected for a Match Lineup!",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()

        except UserProfile.DoesNotExist:
            logger.debug(f"No user profile found for player {instance.player.id}. Skipping notification.")
        except Exception as e:
            logger.error(f"Error sending lineup add notification for player {instance.player.id}: {e}", exc_info=True)


@receiver(post_delete, sender=LineupPlayer)
def send_lineup_remove_notification(sender, instance, **kwargs):
    """Send notification to player when removed from a lineup."""
    logger.debug(f"send_lineup_remove_notification triggered for player {instance.player.id}")
    try:
        user = instance.player.userprofile.user
        logger.debug(f"User found for notification: {user.username}")
        match_info = f"{instance.lineup.match.home_team} vs {instance.lineup.match.away_team} on {instance.lineup.match.date.strftime('%Y-%m-%d')}"

        # Create in-app notification
        Notification.objects.create(
            user=user,
            title="You've been removed from a match lineup",
            message=f"You have been removed from the lineup for the match: {match_info}."
        )

        # Prepare email context
        context = {
            'player_name': user.first_name or user.username,
            'match': instance.lineup.match,
            'added': False,
            'match_url': settings.BASE_URL + reverse('match_details', args=[instance.lineup.match.id]),
        }

        # Render HTML and text versions
        html_content = render_to_string('emails/lineup_notification.html', context)
        text_content = f"Hi {context['player_name']},\n\nYou have been removed from the lineup for the match: {match_info}.\n\nSee the updated lineup: {context['match_url']}"

        # Send email
        msg = EmailMultiAlternatives(
            subject="Lineup Update for Your Upcoming Match",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    except UserProfile.DoesNotExist:
        logger.debug(f"No user profile found for player {instance.player.id}. Skipping notification.")
    except Exception as e:
        logger.error(f"Error sending lineup remove notification for player {instance.player.id}: {e}", exc_info=True)