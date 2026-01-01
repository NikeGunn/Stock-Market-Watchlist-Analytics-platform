"""
Celery tasks for notifications app.

Alert evaluation and notification delivery.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def evaluate_price_alerts():
    """
    Evaluate all active price alerts and trigger notifications.
    
    WHY PERIODIC?
    We check alerts every 5 minutes to catch price changes.
    
    PROCESS:
    1. Get all active alerts
    2. Check each alert's condition against latest price
    3. If triggered, create notification and send email
    4. Mark alert as triggered (if one_time=True)
    
    SCHEDULED: Every 5 minutes (configured in celery.py)
    """
    from .models import PriceAlert
    from pricing.models import StockPrice
    
    try:
        # Get all active, non-triggered alerts
        alerts = PriceAlert.objects.active_alerts().select_related('stock', 'user')
        
        logger.info(f'Evaluating {alerts.count()} price alerts')
        
        triggered_count = 0
        
        for alert in alerts:
            # Get latest price for this stock
            latest_price = StockPrice.objects.latest_price(alert.stock)
            
            if not latest_price:
                continue
            
            # Check if alert condition is met
            if alert.check_condition(latest_price):
                # Trigger the alert
                alert.trigger()
                
                # Create notification
                send_price_alert_notification.delay(alert.id, latest_price.price)
                
                triggered_count += 1
                logger.info(f'Alert triggered for {alert.user.email}: {alert.stock.symbol}')
            
            # Update last_checked_at
            alert.last_checked_at = timezone.now()
            alert.save(update_fields=['last_checked_at'])
        
        return {'evaluated': alerts.count(), 'triggered': triggered_count}
    
    except Exception as e:
        logger.error(f'Error evaluating alerts: {e}')
        raise


@shared_task(bind=True, max_retries=3)
def send_price_alert_notification(self, alert_id, current_price):
    """
    Send notification for triggered price alert.
    
    WHY SEPARATE TASK?
    - Email sending can fail (network issues)
    - Retryable (max 3 attempts)
    - Doesn't block alert evaluation
    """
    from .models import PriceAlert, Notification
    
    try:
        alert = PriceAlert.objects.select_related('user', 'stock').get(id=alert_id)
        
        # Create notification record
        subject = f'Price Alert: {alert.stock.symbol}'
        
        message = f"""
        Your price alert for {alert.stock.name} ({alert.stock.symbol}) has been triggered!
        
        Alert Condition: {alert.get_condition_type_display()}
        Threshold: ${alert.threshold_value}
        Current Price: ${current_price}
        
        View your watchlist: {settings.FRONTEND_URL}/watchlist/
        
        Best regards,
        Stock Watchlist Team
        """
        
        notification = Notification.objects.create(
            user=alert.user,
            alert=alert,
            notification_type='PRICE_ALERT',
            channel='EMAIL',
            subject=subject,
            message=message,
            status='PENDING'
        )
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert.user.email],
                fail_silently=False
            )
            
            notification.mark_as_sent()
            logger.info(f'Alert notification sent to {alert.user.email}')
            
            return {'status': 'success', 'notification_id': str(notification.id)}
        
        except Exception as email_error:
            notification.mark_as_failed(email_error)
            logger.error(f'Failed to send email: {email_error}')
            raise
    
    except Exception as exc:
        logger.error(f'Notification task failed: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_bulk_notifications(user_ids, subject, message):
    """
    Send bulk notifications to multiple users.
    
    WHY: Admin might want to send announcements.
    Example: "System maintenance scheduled"
    """
    from accounts.models import User
    from .models import Notification
    
    try:
        users = User.objects.filter(id__in=user_ids, is_active=True)
        
        sent_count = 0
        
        for user in users:
            notification = Notification.objects.create(
                user=user,
                notification_type='SYSTEM',
                channel='EMAIL',
                subject=subject,
                message=message,
                status='PENDING'
            )
            
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
                
                notification.mark_as_sent()
                sent_count += 1
            
            except Exception as e:
                notification.mark_as_failed(e)
                logger.error(f'Failed to send to {user.email}: {e}')
        
        logger.info(f'Bulk notification sent to {sent_count}/{users.count()} users')
        return {'sent': sent_count, 'total': users.count()}
    
    except Exception as e:
        logger.error(f'Bulk notification failed: {e}')
        raise


@shared_task
def cleanup_old_notifications():
    """
    Delete old read notifications.
    
    WHY: Keep database clean.
    Users don't need notifications from 6 months ago.
    
    RETENTION: Keep unread forever, delete read after 90 days.
    """
    from .models import Notification
    from datetime import timedelta
    
    # Delete read notifications older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count = Notification.objects.filter(
        read_at__isnull=False,
        read_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f'Cleaned up {deleted_count} old notifications')
    
    return {'deleted': deleted_count}
