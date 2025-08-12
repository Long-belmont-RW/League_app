from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
from league.models import Coach, CoachRoles, Player
from django.db import transaction
import logging


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

            # Optional: Handle cases where a user's role changes from 'coach'/'player' to something else.
            # You might want to unlink or delete the Coach/Player object here.
            # This logic can become complex if you need to manage transitions between roles.
            # For simplicity, this signal focuses on creation and linking.
            # Example: if instance.role not in ['coach', 'player'] and user_profile.coach:
            #     user_profile.coach = None
            #     user_profile.save()
            #     logger.info(f"Unlinked Coach from UserProfile for user {instance.username} due to role change.")

        except Exception as e:
            logger.error(f"Error in post_save signal for User {instance.username} (ID: {instance.id}): {e}", exc_info=True)
            raise # Re-raise to ensure the transaction is rolled back


@receiver(post_delete, sender=Coach)
def delete_user_profile_on_coach_delete(sender, instance, **kwargs):
    """
    Signal handler to delete the associated UserProfile and User when a Coach object is deleted.
    This ensures that if a Coach is removed, their profile and user account are also cleaned up.

    Args:
        sender: The model class that sent the signal (Coach in this case).
        instance: The actual instance of the Coach that was just deleted.
        kwargs: Additional keyword arguments.
    """
    with transaction.atomic():
        try:
            # Find the UserProfile that was linked to this deleted Coach instance.
            # We use select_related('user') to optimize fetching the related User object
            # if we needed to access its attributes directly, though for deletion, it's not strictly necessary
            # as CASCADE will handle the User deletion.
            user_profile = UserProfile.objects.select_related('user').get(coach=instance)

            # Log the user and profile being deleted before deletion
            user_username = user_profile.user.username if user_profile.user else "N/A"
            logger.info(
                f"Deleting UserProfile (ID: {user_profile.id}) and User (Username: {user_username}) "
                f"due to Coach (ID: {instance.id}) deletion."
            )

            # Delete the UserProfile.
            # This will automatically trigger the deletion of the associated User
            # because UserProfile.user has on_delete=models.CASCADE.
            user_profile.delete()

        except UserProfile.DoesNotExist:
            # This can happen if the UserProfile was already deleted, or never existed for this coach.
            logger.warning(f"No UserProfile found for deleted Coach (ID: {instance.id}). No action needed.")
        except Exception as e:
            logger.error(f"Error deleting UserProfile/User for Coach (ID: {instance.id}): {e}", exc_info=True)
            # Re-raise to ensure the transaction rolls back if this is part of a larger operation
            raise


@receiver(post_delete, sender=Player)
def delete_user_profile_on_player_delete(sender, instance, **kwargs):
    """
    Signal handler to delete the associated UserProfile and User when a Player object is deleted.
    This ensures that if a Player is removed, their profile and user account are also cleaned up.

    Args:
        sender: The model class that sent the signal (Player in this case).
        instance: The actual instance of the Player that was just deleted.
        kwargs: Additional keyword arguments.
    """
    with transaction.atomic():
        try:
            # Find the UserProfile that was linked to this deleted Player instance.
            user_profile = UserProfile.objects.select_related('user').get(player=instance)

            # Log the user and profile being deleted before deletion
            user_username = user_profile.user.username if user_profile.user else "N/A"
            logger.info(
                f"Deleting UserProfile (ID: {user_profile.id}) and User (Username: {user_username}) "
                f"due to Player (ID: {instance.id}) deletion."
            )

            # Delete the UserProfile.
            # This will automatically trigger the deletion of the associated User
            # because UserProfile.user has on_delete=models.CASCADE.
            user_profile.delete()

        except UserProfile.DoesNotExist:
            # This can happen if the UserProfile was already deleted, or never existed for this player.
            logger.warning(f"No UserProfile found for deleted Player (ID: {instance.id}). No action needed.")
        except Exception as e:
            logger.error(f"Error deleting UserProfile/User for Player (ID: {instance.id}): {e}", exc_info=True)
            # Re-raise to ensure the transaction rolls back if this is part of a larger operation
            raise



