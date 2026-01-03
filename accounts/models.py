"""
Custom User model and Profile model.

WHY CUSTOM USER MODEL?
Django's default User model is limited. We need:
1. Email as the primary identifier (not username)
2. Custom fields like timezone, preferred currency
3. Soft deletion instead of hard delete

WHY PROFILE MODEL?
Separation of concerns: Authentication data (User) vs. User preferences (Profile).
This follows the Single Responsibility Principle.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.crypto import get_random_string
import uuid
import secrets
import hashlib


class UserManager(BaseUserManager):
    """
    Custom manager for User model.
    
    WHY CUSTOM MANAGER?
    We override the default manager to use email instead of username.
    Managers handle database queries - they're the interface between model and database.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Hashes the password
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the unique identifier.
    
    FIELDS EXPLANATION:
    - id: UUID for better security (harder to guess than sequential IDs)
    - email: Primary identifier, must be unique
    - is_active: For soft deletion (deactivate instead of delete)
    - is_staff: Can access admin panel
    - is_superuser: Has all permissions (from PermissionsMixin)
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'  # Use email for authentication
    REQUIRED_FIELDS = []  # Email is already required
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return full name."""
        return f'{self.first_name} {self.last_name}'.strip() or self.email
    
    def soft_delete(self):
        """
        Soft delete - deactivate instead of deleting.
        
        WHY SOFT DELETE?
        1. Preserve data integrity (foreign key references)
        2. Comply with regulations (audit trails)
        3. Allow account recovery
        """
        self.is_active = False
        self.save(update_fields=['is_active'])


class Profile(models.Model):
    """
    User profile with additional information and preferences.
    
    WHY SEPARATE MODEL?
    - Keeps User model clean (only authentication data)
    - Profile can be extended without modifying User
    - OneToOne relationship means one profile per user
    """
    
    ACCOUNT_TIERS = [
        ('STANDARD', 'Standard'),
        ('PREMIUM', 'Premium'),
        ('ADMIN', 'Admin'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('INR', 'Indian Rupee'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    account_tier = models.CharField(
        max_length=20,
        choices=ACCOUNT_TIERS,
        default='STANDARD',
        db_index=True,  # Indexed for performance (we query this often)
    )
    timezone = models.CharField(max_length=50, default='UTC')
    preferred_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD'
    )
    
    # Watchlist limits based on tier
    max_watchlists = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['account_tier']),
        ]
    
    def __str__(self):
        return f'{self.user.email} - {self.account_tier}'
    
    def save(self, *args, **kwargs):
        """
        Override save to set max_watchlists based on tier.
        
        WHY OVERRIDE SAVE?
        Business logic: Different tiers have different limits.
        We enforce this at the model level for consistency.
        """
        if self.account_tier == 'STANDARD':
            self.max_watchlists = 1
        elif self.account_tier == 'PREMIUM':
            self.max_watchlists = 10
        else:  # ADMIN
            self.max_watchlists = 999
        
        super().save(*args, **kwargs)


class APIKeyManager(models.Manager):
    """
    Custom manager for APIKey model.
    """
    
    def create_key(self, user, name):
        """
        Create a new API key for a user.
        
        Returns:
            tuple: (api_key_instance, raw_key)
            The raw_key should be shown to user only once!
        """
        # Generate secure random key
        raw_key = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
        
        # Hash the key before storing (like passwords)
        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = self.create(
            user=user,
            name=name,
            key=hashed_key
        )
        
        return (api_key, raw_key)
    
    def active_keys(self):
        """Return only active API keys."""
        return self.filter(is_active=True)


class APIKey(models.Model):
    """
    API Key model for internal service authentication.
    
    WHY API KEYS?
    - Internal services need to authenticate without user credentials
    - Long-lived tokens for automated processes
    - Can be revoked/rotated without changing passwords
    
    SECURITY:
    - Keys are hashed (SHA-256) before storage
    - Keys can be revoked individually
    - Track usage (last_used_at) for auditing
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text='Service account or user this key belongs to'
    )
    
    name = models.CharField(
        max_length=100,
        help_text='Descriptive name for this key (e.g., "Price Fetcher Service")'
    )
    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='Hashed API key (SHA-256)'
    )
    
    is_active = models.BooleanField(default=True)
    
    # Usage tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Optional expiration date'
    )
    
    objects = APIKeyManager()
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f'{self.user.email} - {self.name}'
    
    def record_usage(self):
        """Update last_used_at timestamp."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def is_valid(self):
        """Check if key is active and not expired."""
        if not self.is_active:
            return False
        
        if self.expires_at and self.expires_at < timezone.now():
            return False
        
        return True
    
    def revoke(self):
        """Revoke this API key."""
        self.is_active = False
        self.save(update_fields=['is_active'])

