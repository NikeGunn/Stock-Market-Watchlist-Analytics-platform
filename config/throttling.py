"""
Custom throttling classes for rate limiting based on user roles.

WHY RATE LIMITING?
- Prevents abuse (DOS attacks, scraping)
- Ensures fair resource usage
- Protects external APIs (we have limited API calls to Alpha Vantage)

Different user tiers get different limits:
- Standard: 100 requests/hour
- Premium: 1000 requests/hour
- Admin: Unlimited
"""

from rest_framework.throttling import UserRateThrottle


class UserRoleThrottle(UserRateThrottle):
    """
    Throttle requests based on user's account tier.
    
    HOW IT WORKS:
    1. Check user's account tier from their profile
    2. Apply corresponding rate limit
    3. Track requests in Redis (fast and distributed)
    4. Return 429 (Too Many Requests) if limit exceeded
    """
    
    # Default rate - will be overridden per request
    rate = '100/hour'
    
    def allow_request(self, request, view):
        """
        Determine if request should be allowed based on user's tier.
        
        WHY: We override this method to set rate dynamically
        based on the user's account tier for each request.
        """
        # Set rate based on user tier before checking
        if not request.user or not request.user.is_authenticated:
            self.rate = '50/hour'  # Anonymous users
        elif request.user.is_staff or request.user.is_superuser:
            return True  # No throttling for admin
        elif hasattr(request.user, 'profile'):
            tier = request.user.profile.account_tier
            if tier == 'ADMIN':
                return True
            elif tier == 'PREMIUM':
                self.rate = '1000/hour'
            else:  # STANDARD
                self.rate = '100/hour'
        else:
            self.rate = '100/hour'  # Default
        
        # Parse the rate
        self.num_requests, self.duration = self.parse_rate(self.rate)
        
        # Call parent's allow_request
        return super().allow_request(request, view)
    
    def get_cache_key(self, request, view):
        """
        Create unique cache key for each user.
        
        WHY: We track requests per user in Redis.
        Each user gets their own counter.
        """
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            # For anonymous users, use IP address
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
