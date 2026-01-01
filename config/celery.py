"""
Celery configuration for Stock Market Watchlist project.

This module configures Celery for handling asynchronous tasks like:
- Stock price ingestion
- Alert evaluation
- Email notifications
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'fetch-stock-prices-every-15-minutes': {
        'task': 'pricing.tasks.fetch_stock_prices',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'evaluate-price-alerts-every-5-minutes': {
        'task': 'notifications.tasks.evaluate_price_alerts',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-stock-prices-daily': {
        'task': 'pricing.tasks.cleanup_old_prices',
        'schedule': crontab(hour=2, minute=0),  # Every day at 2 AM
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
