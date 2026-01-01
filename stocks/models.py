"""
Stock master data model.

WHY SEPARATE FROM PRICES?
- Stock info (name, symbol) changes rarely
- Price data changes constantly (every minute/second)
- Different access patterns: Stocks are referenced, Prices are time-series
- This separation allows better indexing and partitioning strategies
"""

from django.db import models
from django.utils import timezone
import uuid


class StockManager(models.Manager):
    """
    Custom manager for Stock model with convenience methods.
    
    WHY CUSTOM MANAGER?
    Managers encapsulate common queries. Instead of writing:
        Stock.objects.filter(is_active=True)
    We can write:
        Stock.objects.active()
    
    This makes code more readable and DRY (Don't Repeat Yourself).
    """
    
    def active(self):
        """Return only active stocks."""
        return self.filter(is_active=True)
    
    def by_exchange(self, exchange):
        """Get stocks by exchange."""
        return self.filter(exchange=exchange, is_active=True)
    
    def search(self, query):
        """
        Search stocks by symbol or name.
        
        WHY __icontains?
        The 'i' means case-insensitive.
        LIKE '%query%' in SQL.
        """
        return self.filter(
            models.Q(symbol__icontains=query) | 
            models.Q(name__icontains=query),
            is_active=True
        )


class Stock(models.Model):
    """
    Stock master data model.
    
    DESIGN DECISIONS:
    - symbol: Unique identifier (e.g., AAPL, GOOGL)
    - is_active: Soft delete (some stocks get delisted but we keep history)
    - No price data here: Prices are in StockPrice model
    """
    
    EXCHANGE_CHOICES = [
        ('NYSE', 'New York Stock Exchange'),
        ('NASDAQ', 'NASDAQ'),
        ('NSE', 'National Stock Exchange of India'),
        ('BSE', 'Bombay Stock Exchange'),
        ('LSE', 'London Stock Exchange'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('INR', 'Indian Rupee'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,  # Indexed because we query by symbol frequently
    )
    name = models.CharField(max_length=255)
    exchange = models.CharField(max_length=20, choices=EXCHANGE_CHOICES, db_index=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    # Metadata
    sector = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    market_cap = models.BigIntegerField(null=True, blank=True, help_text='Market cap in millions')
    
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = StockManager()
    
    class Meta:
        db_table = 'stocks'
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'
        ordering = ['symbol']
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['exchange']),
            models.Index(fields=['is_active']),
            # Composite index for common query pattern
            models.Index(fields=['exchange', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.symbol} - {self.name}'
    
    def soft_delete(self):
        """Soft delete - mark as inactive."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
