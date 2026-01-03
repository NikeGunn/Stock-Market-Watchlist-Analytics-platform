"""
Django admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, APIKey


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model."""
    
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Admin for Profile model."""
    
    list_display = ['user', 'account_tier', 'preferred_currency', 'max_watchlists', 'created_at']
    list_filter = ['account_tier', 'preferred_currency', 'created_at']
    search_fields = ['user__email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Account Settings', {'fields': ('account_tier', 'timezone', 'preferred_currency')}),
        ('Limits', {'fields': ('max_watchlists',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin for APIKey model."""
    
    list_display = ['name', 'user', 'is_active', 'created_at', 'last_used_at', 'expires_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__email']
    ordering = ['-created_at']
    readonly_fields = ['key', 'created_at', 'last_used_at']
    
    fieldsets = (
        ('Key Info', {'fields': ('user', 'name', 'key')}),
        ('Status', {'fields': ('is_active', 'expires_at')}),
        ('Tracking', {'fields': ('created_at', 'last_used_at')}),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Override save to handle key generation for new API keys.
        
        Note: The raw key cannot be shown after initial creation.
        Consider creating API keys via management command instead.
        """
        if not change:  # Only for new objects
            # Generate key if not set
            if not obj.key:
                import secrets
                import hashlib
                raw_key = secrets.token_urlsafe(32)
                obj.key = hashlib.sha256(raw_key.encode()).hexdigest()
                # Log the raw key for admin (in production, use secure method)
                self.message_user(
                    request,
                    f'API Key created. Raw key (save this now!): {raw_key}',
                    level='WARNING'
                )
        super().save_model(request, obj, form, change)
