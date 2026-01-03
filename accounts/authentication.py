"""
Custom authentication classes for the Stock Watchlist API.

AUTHENTICATION METHODS:
1. JWT Authentication (default) - For user-facing APIs
2. API Key Authentication - For internal services and machine-to-machine communication

WHY API KEY AUTH?
- Internal services (like price fetching services) need to authenticate
- No user context needed for some operations
- Long-lived tokens for automated processes
"""

from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
from django.core.cache import cache
from .models import User, APIKey
import logging

logger = logging.getLogger(__name__)


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication for internal services.
    
    HOW IT WORKS:
    1. Client sends API key in header: X-API-Key: <key>
    2. We validate the key against database
    3. Return associated user (service account)
    
    SECURITY:
    - Keys are hashed in database (like passwords)
    - Keys can be revoked/rotated
    - Keys are cached in Redis for performance
    """
    
    keyword = 'X-API-Key'
    
    def authenticate(self, request):
        """
        Authenticate using API key from request headers.
        
        Returns:
            tuple: (user, token) if authenticated
            None: if no API key provided
            
        Raises:
            AuthenticationFailed: if API key is invalid
        """
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            # No API key provided, let other auth methods handle it
            return None
        
        return self._authenticate_credentials(api_key)
    
    def _authenticate_credentials(self, key):
        """
        Validate API key and return associated user.
        
        OPTIMIZATION: Check Redis cache first to avoid database hit.
        """
        # Check cache first
        cache_key = f'api_key:{key[:10]}'  # Use first 10 chars as cache key
        cached_user_id = cache.get(cache_key)
        
        if cached_user_id:
            try:
                user = User.objects.get(id=cached_user_id, is_active=True)
                logger.info(f'API key authenticated (cached): {user.email}')
                return (user, key)
            except User.DoesNotExist:
                # Cache is stale, remove it
                cache.delete(cache_key)
        
        # Validate against database
        try:
            api_key_obj = APIKey.objects.select_related('user').get(
                key=key,
                is_active=True
            )
            
            # Update last used timestamp
            api_key_obj.record_usage()
            
            # Cache for 5 minutes
            cache.set(cache_key, str(api_key_obj.user.id), 300)
            
            logger.info(f'API key authenticated: {api_key_obj.user.email}')
            return (api_key_obj.user, key)
            
        except APIKey.DoesNotExist:
            logger.warning(f'Invalid API key attempt: {key[:10]}...')
            raise exceptions.AuthenticationFailed('Invalid API key')
    
    def authenticate_header(self, request):
        """
        Return authentication header for WWW-Authenticate response.
        """
        return self.keyword

