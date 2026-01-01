"""
URL routing for notifications app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PriceAlertViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'alerts', PriceAlertViewSet, basename='alert')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
