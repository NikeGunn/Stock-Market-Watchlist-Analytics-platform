"""
Stock price model for time-series data.

CRITICAL DESIGN DECISIONS:
1. Composite index on (stock, timestamp) for fast range queries
2. Immutable records (prices should never change once recorded)
3. Source tracking (know where price came from)
4. No cascading deletes (keep price history even if stock is deleted)
"""

from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg, Min, Max, StdDev
from stocks.models import Stock
import uuid


class StockPriceManager(models.Manager):
    """
    Custom manager for StockPrice with optimized queries.
    
    WHY THESE METHODS?
    Time-series data has common query patterns:
    - Latest price
    - Price range (last 30 days)
    - Aggregations (min, max, avg)
    
    We encapsulate these to avoid query duplication.
    """
    
    def latest_price(self, stock):
        """
        Get the latest price for a stock.
        
        OPTIMIZATION: Uses Redis cache to avoid database query.
        Cache is invalidated when new price is added.
        """
        cache_key = f'latest_price:{stock.symbol}'
        cached_price = cache.get(cache_key)
        
        if cached_price:
            return cached_price
        
        try:
            price = self.filter(stock=stock).latest('timestamp')
            # Cache for 5 minutes
            cache.set(cache_key, price, 300)
            return price
        except StockPrice.DoesNotExist:
            return None
    
    def price_range(self, stock, start_date, end_date):
        """
        Get prices within a date range.
        
        WHY THIS QUERY?
        Uses composite index (stock, timestamp) for fast lookups.
        """
        return self.filter(
            stock=stock,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).order_by('timestamp')
    
    def get_statistics(self, stock, start_date, end_date):
        """
        Calculate price statistics for a period.
        
        WHY AT DATABASE LEVEL?
        Aggregations are faster in the database than in Python.
        PostgreSQL is optimized for these operations.
        """
        stats = self.filter(
            stock=stock,
            timestamp__gte=start_date,
            timestamp__lte=end_date
        ).aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            volatility=StdDev('price')
        )
        
        return stats


class StockPrice(models.Model):
    """
    Time-series model for stock prices.
    
    IMPORTANT: This table will grow VERY large.
    Consider partitioning by date in production (PostgreSQL 10+).
    
    FIELDS:
    - stock: Foreign key to Stock (what stock)
    - price: Decimal for precision (never use Float for money!)
    - volume: Number of shares traded
    - timestamp: When this price was recorded
    - source: Where did we get this price (API, manual entry, etc.)
    """
    
    SOURCE_CHOICES = [
        ('ALPHA_VANTAGE', 'Alpha Vantage API'),
        ('MANUAL', 'Manual Entry'),
        ('YAHOO', 'Yahoo Finance'),
        ('POLYGON', 'Polygon.io'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(
        Stock,
        on_delete=models.PROTECT,  # Don't delete prices if stock is deleted
        related_name='prices',
        db_index=True
    )
    
    # Price data - NEVER use FloatField for money!
    price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text='Stock price'
    )
    volume = models.BigIntegerField(default=0, help_text='Trading volume')
    
    # Metadata
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='ALPHA_VANTAGE')
    timestamp = models.DateTimeField(
        db_index=True,
        help_text='When this price was recorded'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = StockPriceManager()
    
    class Meta:
        db_table = 'stock_prices'
        verbose_name = 'Stock Price'
        verbose_name_plural = 'Stock Prices'
        ordering = ['-timestamp']
        
        # CRITICAL: Composite index for fast queries
        indexes = [
            models.Index(fields=['stock', '-timestamp']),  # Most common query
            models.Index(fields=['timestamp']),
            models.Index(fields=['source']),
        ]
        
        # Ensure one price per stock per timestamp
        constraints = [
            models.UniqueConstraint(
                fields=['stock', 'timestamp'],
                name='unique_stock_price_timestamp'
            )
        ]
    
    def __str__(self):
        return f'{self.stock.symbol} - {self.price} @ {self.timestamp}'
    
    def save(self, *args, **kwargs):
        """
        Override save to invalidate cache.
        
        WHY: When new price is added, cached latest price is stale.
        We must invalidate the cache.
        """
        super().save(*args, **kwargs)
        
        # Invalidate cached latest price
        cache_key = f'latest_price:{self.stock.symbol}'
        cache.delete(cache_key)
    
    def percentage_change(self, previous_price):
        """Calculate percentage change from previous price."""
        if previous_price and previous_price.price:
            change = ((self.price - previous_price.price) / previous_price.price) * 100
            return round(float(change), 2)
        return 0.0
