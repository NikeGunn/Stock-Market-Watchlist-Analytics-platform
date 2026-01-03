"""
Tests for accounts app.

WHY TESTING?
1. Catch bugs before production
2. Document expected behavior
3. Enable safe refactoring
4. Build confidence

TEST TYPES:
- Unit tests: Test individual functions/methods
- Integration tests: Test multiple components together
- API tests: Test HTTP endpoints

PYTEST vs UNITTEST:
Using pytest-django for cleaner syntax and better fixtures.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import Profile

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """
    Unit tests for User model.
    
    WHY @pytest.mark.django_db?
    Tells pytest this test needs database access.
    """
    
    def test_create_user(self):
        """Test creating a user with email."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        assert user.email == 'test@example.com'
        assert user.is_active is True
        assert user.is_staff is False
        assert user.check_password('testpass123')
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        assert user.is_staff is True
        assert user.is_superuser is True
    
    def test_user_str(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123'
        )
        
        assert str(user) == 'test@example.com'
    
    def test_profile_created_on_user_creation(self):
        """Test that profile is automatically created when user is created."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123'
        )
        
        # Check profile exists
        assert hasattr(user, 'profile')
        assert user.profile.account_tier == 'STANDARD'
        assert user.profile.max_watchlists == 1


@pytest.mark.django_db
class TestProfileModel:
    """Unit tests for Profile model."""
    
    def test_profile_tier_limits(self):
        """Test that profile sets correct watchlist limits based on tier."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123'
        )
        
        profile = user.profile
        
        # Standard user
        assert profile.max_watchlists == 1
        
        # Upgrade to premium
        profile.account_tier = 'PREMIUM'
        profile.save()
        assert profile.max_watchlists == 10
        
        # Upgrade to admin
        profile.account_tier = 'ADMIN'
        profile.save()
        assert profile.max_watchlists == 999


@pytest.mark.django_db
class TestUserAPI:
    """
    Integration tests for User API endpoints.
    
    WHY INTEGRATION TESTS?
    Test the full request/response cycle including:
    - Serialization
    - Validation
    - Permissions
    - Database operations
    """
    
    @pytest.fixture
    def api_client(self):
        """Create API client for tests."""
        return APIClient()
    
    @pytest.fixture
    def create_user(self):
        """Factory fixture for creating users."""
        def _create_user(email='test@example.com', password='testpass123', **kwargs):
            return User.objects.create_user(email=email, password=password, **kwargs)
        return _create_user
    
    def test_register_user(self, api_client):
        """Test user registration endpoint."""
        data = {
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        
        response = api_client.post('/api/v1/accounts/users/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'data' in response.data
        assert response.data['data']['email'] == 'newuser@example.com'
        
        # Verify user was created in database
        user = User.objects.get(email='newuser@example.com')
        assert user.first_name == 'John'
        assert user.profile is not None
    
    def test_register_user_password_mismatch(self, api_client):
        """Test registration fails with password mismatch."""
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'password2': 'different456'
        }
        
        response = api_client.post('/api/v1/accounts/users/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'errors' in response.data
    
    def test_get_current_user_profile(self, api_client, create_user):
        """Test getting current user's profile."""
        user = create_user()
        api_client.force_authenticate(user=user)
        
        response = api_client.get('/api/v1/accounts/users/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['email'] == user.email
        assert 'profile' in response.data['data']
    
    def test_get_profile_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot access profile."""
        response = api_client.get('/api/v1/accounts/users/me/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile(self, api_client, create_user):
        """Test updating user profile."""
        user = create_user()
        api_client.force_authenticate(user=user)
        
        data = {
            'timezone': 'America/New_York',
            'preferred_currency': 'EUR'
        }
        
        response = api_client.put('/api/v1/accounts/users/update_profile/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify changes in database
        user.profile.refresh_from_db()
        assert user.profile.timezone == 'America/New_York'
        assert user.profile.preferred_currency == 'EUR'
    
    def test_change_password(self, api_client, create_user):
        """Test password change endpoint."""
        user = create_user(password='oldpassword123')
        api_client.force_authenticate(user=user)
        
        data = {
            'old_password': 'oldpassword123',
            'new_password': 'newpassword456',
            'new_password2': 'newpassword456'
        }
        
        response = api_client.post('/api/v1/accounts/users/change_password/', data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password('newpassword456')
    
    def test_change_password_wrong_old_password(self, api_client, create_user):
        """Test password change fails with wrong old password."""
        user = create_user(password='correctpassword')
        api_client.force_authenticate(user=user)
        
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword456',
            'new_password2': 'newpassword456'
        }
        
        response = api_client.post('/api/v1/accounts/users/change_password/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# Run tests with:
# pytest accounts/tests.py -v
# pytest accounts/tests.py -v --cov=accounts --cov-report=html
