"""
URL routing for watchlists app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WatchlistViewSet, WatchlistItemViewSet

router = DefaultRouter()
router.register(r'watchlists', WatchlistViewSet, basename='watchlist')
router.register(r'items', WatchlistItemViewSet, basename='watchlistitem')

urlpatterns = [
    path('', include(router.urls)),
]
