"""
Django signals for accounts app.

WHY SIGNALS?
Signals are Django's way of allowing decoupled apps to get notified when actions occur.
Think of them as event listeners.

EXAMPLE: When a User is created, we automatically create a Profile.
This keeps code clean - Profile creation logic isn't in the User model.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Profile when a User is created.
    
    WHY: Every user needs a profile. This ensures it's never forgotten.
    The signal fires AFTER the user is saved to the database.
    """
    if created:
        Profile.objects.create(user=instance)
        logger.info(f'Profile created for user: {instance.email}')


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the profile when user is saved.
    
    WHY: Keeps user and profile in sync.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
