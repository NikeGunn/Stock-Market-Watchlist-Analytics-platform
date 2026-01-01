"""
Health check endpoints for monitoring system status.

WHY: In production, we need to monitor if our services are healthy:
- Liveness: Is the app running? (for auto-restart)
- Readiness: Can the app handle requests? (for load balancers)
- Detailed health: Check database, Redis, Celery connections
"""

from django.urls import path
from . import health_views

urlpatterns = [
    path('', health_views.health_check, name='health'),
    path('liveness/', health_views.liveness, name='liveness'),
    path('readiness/', health_views.readiness, name='readiness'),
]
