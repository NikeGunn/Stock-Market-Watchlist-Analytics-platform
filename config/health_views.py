"""
Health check views for monitoring system status.

WHY: Kubernetes, Docker, and load balancers need health endpoints to:
1. Know when to restart containers (liveness)
2. Know when to route traffic (readiness)
3. Monitor overall system health
"""

from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from celery.app.control import Control
from config.celery import app as celery_app
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Detailed health check with all service statuses.
    
    WHY: Ops team needs to see which specific service is failing.
    Example: If Redis is down, we know caching is broken.
    """
    health_status = {
        'status': 'healthy',
        'checks': {
            'database': check_database(),
            'cache': check_cache(),
            'celery': check_celery(),
        }
    }
    
    # If any check fails, overall status is unhealthy
    if not all(check['status'] == 'healthy' for check in health_status['checks'].values()):
        health_status['status'] = 'unhealthy'
        status_code = 503  # Service Unavailable
    else:
        status_code = 200
    
    return JsonResponse(health_status, status=status_code)


def liveness(request):
    """
    Liveness probe - is the application running?
    
    WHY: Kubernetes uses this to know if it should restart the container.
    If this returns 500, Kubernetes will kill and restart the pod.
    """
    return JsonResponse({'status': 'alive'}, status=200)


def readiness(request):
    """
    Readiness probe - can the application handle requests?
    
    WHY: Load balancers use this to know if they should send traffic here.
    If this returns 503, no traffic will be routed to this instance.
    """
    # Check critical services
    db_ok = check_database()['status'] == 'healthy'
    cache_ok = check_cache()['status'] == 'healthy'
    
    if db_ok and cache_ok:
        return JsonResponse({'status': 'ready'}, status=200)
    else:
        return JsonResponse({'status': 'not ready'}, status=503)


def check_database():
    """Check database connectivity."""
    try:
        connections['default'].cursor()
        return {'status': 'healthy', 'message': 'Database connection successful'}
    except Exception as e:
        logger.error(f'Database health check failed: {e}')
        return {'status': 'unhealthy', 'message': str(e)}


def check_cache():
    """Check Redis cache connectivity."""
    try:
        cache.set('health_check', 'ok', 10)
        value = cache.get('health_check')
        if value == 'ok':
            return {'status': 'healthy', 'message': 'Cache connection successful'}
        else:
            return {'status': 'unhealthy', 'message': 'Cache read/write failed'}
    except Exception as e:
        logger.error(f'Cache health check failed: {e}')
        return {'status': 'unhealthy', 'message': str(e)}


def check_celery():
    """Check Celery worker connectivity."""
    try:
        # Check if any workers are available
        control = Control(celery_app)
        stats = control.inspect().stats()
        
        if stats:
            return {'status': 'healthy', 'message': f'{len(stats)} worker(s) available'}
        else:
            return {'status': 'unhealthy', 'message': 'No workers available'}
    except Exception as e:
        logger.error(f'Celery health check failed: {e}')
        return {'status': 'unhealthy', 'message': str(e)}
