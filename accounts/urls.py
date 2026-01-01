"""
URL routing for accounts app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

# DRF Router automatically generates URLs for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
