"""
URL routing for pricing app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StockPriceViewSet

router = DefaultRouter()
router.register(r'prices', StockPriceViewSet, basename='price')

urlpatterns = [
    path('', include(router.urls)),
]
