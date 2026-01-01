"""
Watchlist and WatchlistItem models.

RELATIONSHIP:
User -> Watchlist (one-to-many: one user can have multiple watchlists)
Watchlist -> WatchlistItem (one-to-many: one watchlist can have multiple stocks)
Stock -> WatchlistItem (one-to-many: one stock can be in multiple watchlists)

This is a many-to-many relationship with extra data (WatchlistItem is the through model).
"""

from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import User
from stocks.models import Stock
import uuid


class WatchlistManager(models.Manager):
    """
    Custom manager for Watchlist model.
    """
    
    def user_watchlists(self, user):
        """Get all watchlists for a user."""
        return self.filter(user=user)
    
    def get_default(self, user):
        """Get user's default watchlist."""
        return self.filter(user=user, is_default=True).first()


class Watchlist(models.Model):
    """
    User's stock watchlist.
    
    BUSINESS RULES:
    - Standard users: 1 watchlist (is_default=True)
    - Premium users: Up to 10 watchlists
    - Admin users: Unlimited watchlists
    
    WHY is_default?
    Standard users have only one watchlist, which is their default.
    Premium users can have multiple, one of which is the default.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='watchlists',
        db_index=True
    )
    name = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = WatchlistManager()
    
    class Meta:
        db_table = 'watchlists'
        verbose_name = 'Watchlist'
        verbose_name_plural = 'Watchlists'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['user', '-created_at']),
        ]
        # Each user can only have one watchlist with a given name
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_watchlist_name'
            )
        ]
    
    def __str__(self):
        return f'{self.user.email} - {self.name}'
    
    def clean(self):
        """
        Validate watchlist creation based on user's tier.
        
        WHY clean()?
        Django's clean() method is called before save().
        Perfect place for complex validation logic.
        """
        if not self.pk:  # Only check on creation
            user_watchlist_count = Watchlist.objects.filter(user=self.user).count()
            max_allowed = self.user.profile.max_watchlists
            
            if user_watchlist_count >= max_allowed:
                raise ValidationError(
                    f'Your account tier allows maximum {max_allowed} watchlist(s). '
                    f'Upgrade to Premium for more watchlists.'
                )
    
    def save(self, *args, **kwargs):
        """
        Override save to handle default watchlist logic.
        
        WHY: Ensure only one default watchlist per user.
        """
        # If this is the first watchlist, make it default
        if not self.pk and not Watchlist.objects.filter(user=self.user).exists():
            self.is_default = True
        
        # If this is being set as default, unset others
        if self.is_default:
            Watchlist.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        
        # Validate before saving
        self.clean()
        super().save(*args, **kwargs)
    
    def get_stock_count(self):
        """Get number of stocks in this watchlist."""
        return self.items.count()


class WatchlistItem(models.Model):
    """
    Individual stock in a watchlist.
    
    WHY SEPARATE MODEL?
    This is a "through" model for the many-to-many relationship.
    We need extra fields like:
    - When was the stock added?
    - Alert thresholds (custom per watchlist)
    
    JSONField for alert_thresholds allows flexible configuration:
    {
        "price_above": 150.00,
        "price_below": 100.00,
        "percent_change": 5.0
    }
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name='items',
        db_index=True
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='watchlist_items',
        db_index=True
    )
    
    # Alert configuration (flexible JSON structure)
    alert_thresholds = models.JSONField(
        default=dict,
        blank=True,
        help_text='Alert thresholds in JSON format'
    )
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'watchlist_items'
        verbose_name = 'Watchlist Item'
        verbose_name_plural = 'Watchlist Items'
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['watchlist', '-added_at']),
            models.Index(fields=['stock']),
        ]
        # Prevent duplicate stocks in the same watchlist
        constraints = [
            models.UniqueConstraint(
                fields=['watchlist', 'stock'],
                name='unique_watchlist_stock'
            )
        ]
    
    def __str__(self):
        return f'{self.watchlist.name} - {self.stock.symbol}'
    
    def get_latest_price(self):
        """
        Get latest price for this stock.
        
        WHY HERE?
        Convenience method - often we want the price when showing watchlist items.
        """
        from pricing.models import StockPrice
        return StockPrice.objects.latest_price(self.stock)
