"""
Custom DRF permissions for role-based access control.

WHY CUSTOM PERMISSIONS?
DRF's default permissions (IsAuthenticated, IsAdminUser) are too simple.
We need fine-grained control based on user tiers.

HOW PERMISSIONS WORK:
1. DRF calls has_permission() for view-level access
2. DRF calls has_object_permission() for object-level access
3. Return True to allow, False to deny

Example:
- Standard user can read their own watchlists
- Premium user can create multiple watchlists  
- Admin can read/write all data
"""

from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to only allow owners of an object or admins to access it.
    
    WHY: Users should only access their own data (watchlists, alerts).
    Admins can access everything for support purposes.
    """
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user owns the object or is admin.
        
        ASSUMPTIONS:
        - Object has a 'user' field (like Watchlist, PriceAlert)
        - OR object IS a User (for profile updates)
        """
        # Admin users have full access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if object is User model
        if hasattr(obj, 'email'):  # It's a User object
            return obj == request.user
        
        # Check if object has user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsPremiumOrAdmin(permissions.BasePermission):
    """
    Permission to only allow premium users or admins.
    
    WHY: Some features are premium-only (multiple watchlists, historical data).
    """
    
    message = 'This feature requires a Premium or Admin account.'
    
    def has_permission(self, request, view):
        """Check if user is premium or admin."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin always has access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check user's account tier
        if hasattr(request.user, 'profile'):
            return request.user.profile.account_tier in ['PREMIUM', 'ADMIN']
        
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read-only access to everyone, write access to admins.
    
    WHY: Stock master data should be managed by admins only.
    Users can read stock info but not modify it.
    
    SAFE_METHODS: GET, HEAD, OPTIONS (read-only)
    UNSAFE_METHODS: POST, PUT, PATCH, DELETE (write)
    """
    
    def has_permission(self, request, view):
        """Check permission based on request method."""
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for admin
        return request.user and (request.user.is_staff or request.user.is_superuser)


class CanAccessHistoricalData(permissions.BasePermission):
    """
    Permission for accessing historical price data beyond 30 days.
    
    WHY: Standard users get limited historical data.
    Premium users get full history.
    
    This is checked in the view based on date range.
    """
    
    message = 'Access to historical data beyond 30 days requires a Premium account.'
    
    def has_permission(self, request, view):
        """
        Allow access based on account tier.
        
        NOTE: The actual date range check happens in the view.
        This permission just checks the tier.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin always has access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # For historical data queries, check in the view
        # This permission is just a marker
        return True


class CanCreateMultipleWatchlists(permissions.BasePermission):
    """
    Permission for creating multiple watchlists.
    
    WHY: Standard users limited to 1 watchlist.
    This is enforced at model level too (defense in depth).
    """
    
    message = 'Creating multiple watchlists requires a Premium account.'
    
    def has_permission(self, request, view):
        """Check if user can create another watchlist."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admin always has access
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # For GET requests (listing), allow all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For POST (creation), check tier and count
        if request.method == 'POST':
            from watchlists.models import Watchlist
            
            current_count = Watchlist.objects.filter(user=request.user).count()
            max_allowed = request.user.profile.max_watchlists
            
            if current_count >= max_allowed:
                return False
        
        return True
