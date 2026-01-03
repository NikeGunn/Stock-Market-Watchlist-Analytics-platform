"""
Alert and Notification models.

WORKFLOW:
1. User creates PriceAlert for a stock
2. Celery task periodically checks if conditions are met
3. If triggered, create Notification and send email
4. Mark alert as triggered (if one_time=True)

WHY TWO MODELS?
- PriceAlert: User's alert configuration (what to monitor)
- Notification: Record of sent notifications (audit trail)
"""

from django.db import models
from django.utils import timezone
from accounts.models import User
from stocks.models import Stock
import uuid


class PriceAlertManager(models.Manager):
    """
    Custom manager for PriceAlert model.
    """
    
    def active_alerts(self):
        """Get all active alerts."""
        return self.filter(is_active=True, triggered_at__isnull=True)
    
    def user_alerts(self, user):
        """Get all alerts for a user."""
        return self.filter(user=user)
    
    def alerts_for_stock(self, stock):
        """Get all active alerts for a stock."""
        return self.filter(stock=stock, is_active=True, triggered_at__isnull=True)


class PriceAlert(models.Model):
    """
    User-configured price alert.
    
    ALERT TYPES:
    1. PRICE_ABOVE: Trigger when price goes above threshold
    2. PRICE_BELOW: Trigger when price goes below threshold
    3. PERCENT_CHANGE: Trigger when price changes by X% within time window
    
    WHY condition_type?
    Flexible alert system. Easy to add new alert types later.
    """
    
    CONDITION_TYPES = [
        ('PRICE_ABOVE', 'Price Above'),
        ('PRICE_BELOW', 'Price Below'),
        ('PERCENT_CHANGE', 'Percent Change'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='price_alerts',
        db_index=True
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name='price_alerts',
        db_index=True
    )
    
    # Alert configuration
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPES)
    threshold_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text='Threshold price or percentage'
    )
    
    # Alert behavior
    one_time = models.BooleanField(
        default=True,
        help_text='If True, alert is disabled after first trigger'
    )
    is_active = models.BooleanField(default=True)
    
    # Tracking
    triggered_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = PriceAlertManager()
    
    class Meta:
        db_table = 'price_alerts'
        verbose_name = 'Price Alert'
        verbose_name_plural = 'Price Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['stock', 'is_active']),
            models.Index(fields=['is_active', 'triggered_at']),
        ]
    
    def __str__(self):
        return f'{self.user.email} - {self.stock.symbol} {self.condition_type}'
    
    def check_condition(self, current_price):
        """
        Check if alert condition is met.
        
        WHY THIS METHOD?
        Encapsulates alert logic. Easy to test and reuse.
        
        Returns:
            bool: True if condition is met, False otherwise
        """
        if not current_price:
            return False
        
        if self.condition_type == 'PRICE_ABOVE':
            return current_price.price > self.threshold_value
        elif self.condition_type == 'PRICE_BELOW':
            return current_price.price < self.threshold_value
        elif self.condition_type == 'PERCENT_CHANGE':
            # For percent change, we need historical data
            # This is simplified - in production, calculate from price history
            return False
        
        return False
    
    def trigger(self):
        """
        Mark alert as triggered.
        
        WHY SEPARATE METHOD?
        Clean separation of concerns. Triggering logic is separate from checking.
        """
        self.triggered_at = timezone.now()
        if self.one_time:
            self.is_active = False
        self.save(update_fields=['triggered_at', 'is_active'])


class Notification(models.Model):
    """
    Record of sent notifications.
    
    WHY STORE NOTIFICATIONS?
    1. Audit trail (know what was sent when)
    2. User can view notification history
    3. Prevent duplicate notifications
    4. Track delivery status
    """
    
    NOTIFICATION_TYPES = [
        ('PRICE_ALERT', 'Price Alert'),
        ('SYSTEM', 'System Notification'),
        ('ACCOUNT', 'Account Notification'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]
    
    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('WEBHOOK', 'Webhook'),
        ('IN_APP', 'In-App'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    alert = models.ForeignKey(
        PriceAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='EMAIL')
    
    # Content
    subject = models.CharField(max_length=255)
    message = models.TextField()
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # For in-app notifications
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = models.Manager()  # Default manager
    
    class NotificationQuerySet(models.QuerySet):
        """Custom queryset for Notification."""
        
        def unread(self):
            """Get unread notifications."""
            return self.filter(read_at__isnull=True)
        
        def by_user(self, user):
            """Get notifications for a specific user."""
            return self.filter(user=user)
        
        def pending(self):
            """Get pending notifications."""
            return self.filter(status='PENDING')
        
        def sent(self):
            """Get successfully sent notifications."""
            return self.filter(status='SENT')
    
    # Override default manager with custom queryset
    objects = NotificationQuerySet.as_manager()
    
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'read_at']),
        ]
    
    def __str__(self):
        return f'{self.user.email} - {self.notification_type} - {self.status}'
    
    def mark_as_sent(self):
        """Mark notification as sent."""
        self.status = 'SENT'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_failed(self, error):
        """Mark notification as failed."""
        self.status = 'FAILED'
        self.error_message = str(error)
        self.save(update_fields=['status', 'error_message'])
    
    def mark_as_read(self):
        """Mark in-app notification as read."""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
