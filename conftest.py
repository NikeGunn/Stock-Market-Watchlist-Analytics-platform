"""
Pytest configuration file.

WHY CONFTEST?
- Shared fixtures across all test files
- Test configuration
- Common test utilities
"""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def standard_user(db):
    """Create a standard user."""
    user = User.objects.create_user(
        email='standard@example.com',
        password='testpass123',
        first_name='Standard',
        last_name='User'
    )
    return user


@pytest.fixture
def premium_user(db):
    """Create a premium user."""
    user = User.objects.create_user(
        email='premium@example.com',
        password='testpass123',
        first_name='Premium',
        last_name='User'
    )
    user.profile.account_tier = 'PREMIUM'
    user.profile.save()
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User.objects.create_superuser(
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    return user


@pytest.fixture
def sample_stock(db):
    """Create a sample stock."""
    from stocks.models import Stock
    
    stock = Stock.objects.create(
        symbol='AAPL',
        name='Apple Inc.',
        exchange='NASDAQ',
        currency='USD'
    )
    return stock


@pytest.fixture
def authenticated_client(api_client, standard_user):
    """Return authenticated API client."""
    api_client.force_authenticate(user=standard_user)
    return api_client
