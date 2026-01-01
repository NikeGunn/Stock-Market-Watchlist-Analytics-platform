"""
URL configuration for Stock Market Watchlist project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Authentication
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API v1
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/stocks/', include('stocks.urls')),
    path('api/v1/watchlists/', include('watchlists.urls')),
    path('api/v1/pricing/', include('pricing.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    
    # Health Check
    path('api/v1/health/', include('config.health_urls')),
]
