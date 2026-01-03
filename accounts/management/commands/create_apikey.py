"""
Management command to create API keys for service accounts.

Usage:
    python manage.py create_apikey --user admin@example.com --name "Price Fetcher Service"
    python manage.py create_apikey --user admin@example.com --name "Internal API" --expires-days 365
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, APIKey


class Command(BaseCommand):
    help = 'Create an API key for a user/service account'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            required=True,
            help='Email of the user to create API key for',
        )
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Descriptive name for the API key',
        )
        parser.add_argument(
            '--expires-days',
            type=int,
            default=None,
            help='Number of days until key expires (optional)',
        )
    
    def handle(self, *args, **options):
        user_email = options['user']
        key_name = options['name']
        expires_days = options['expires_days']
        
        try:
            user = User.objects.get(email=user_email, is_active=True)
        except User.DoesNotExist:
            raise CommandError(f'User with email "{user_email}" does not exist or is inactive')
        
        # Create API key
        api_key, raw_key = APIKey.objects.create_key(user=user, name=key_name)
        
        # Set expiration if specified
        if expires_days:
            api_key.expires_at = timezone.now() + timedelta(days=expires_days)
            api_key.save()
        
        self.stdout.write(self.style.SUCCESS(f'\nAPI Key created successfully!'))
        self.stdout.write(f'User: {user.email}')
        self.stdout.write(f'Name: {api_key.name}')
        self.stdout.write(f'Created: {api_key.created_at}')
        if api_key.expires_at:
            self.stdout.write(f'Expires: {api_key.expires_at}')
        
        self.stdout.write(self.style.WARNING(f'\n⚠️  IMPORTANT: Save this API key now! It cannot be retrieved later.'))
        self.stdout.write(self.style.WARNING(f'\nAPI Key: {raw_key}\n'))
        
        self.stdout.write(self.style.SUCCESS('Use this key in the X-API-Key header for API requests.'))
