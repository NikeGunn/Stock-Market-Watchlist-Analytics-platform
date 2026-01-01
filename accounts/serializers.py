"""
Serializers for accounts app.

WHY SERIALIZERS?
Serializers convert between complex data types (Django models) and Python/JSON.
They handle:
1. Validation (is this email valid?)
2. Transformation (hash passwords before saving)
3. Nested relationships (include profile with user)

Think of serializers as translators between database and API.
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Profile


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile.
    
    WHY SEPARATE?
    Profile is separate model, so separate serializer.
    Can be nested in UserSerializer or used independently.
    """
    
    class Meta:
        model = Profile
        fields = [
            'id', 'account_tier', 'timezone', 'preferred_currency',
            'max_watchlists', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'max_watchlists', 'created_at', 'updated_at']
    
    def validate_account_tier(self, value):
        """
        Prevent users from upgrading their own tier via API.
        
        WHY: Security! Users shouldn't be able to make themselves admin.
        Only staff can change tiers (done via admin panel).
        """
        request = self.context.get('request')
        if request and not request.user.is_staff:
            # Get the original tier
            instance = self.instance
            if instance and instance.account_tier != value:
                raise serializers.ValidationError(
                    'You cannot change your account tier. Please contact support.'
                )
        return value


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model (read operations).
    
    WHY SEPARATE FROM REGISTRATION?
    Different use cases need different fields:
    - Registration: needs password
    - Profile view: doesn't show password
    - User list: minimal info
    """
    
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'date_joined', 'last_login', 'profile'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    WHY password1 and password2?
    Common pattern: Ask user to type password twice to prevent typos.
    """
    
    password = serializers.CharField(
        write_only=True,  # Never send password in response
        required=True,
        validators=[validate_password],  # Django's built-in password validation
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password2', 'first_name', 'last_name']
    
    def validate(self, attrs):
        """
        Check that passwords match.
        
        WHY validate() instead of validate_password()?
        validate() receives all fields, perfect for comparing two fields.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password': 'Password fields must match.'
            })
        return attrs
    
    def create(self, validated_data):
        """
        Create user with hashed password.
        
        WHY OVERRIDE create()?
        We need to:
        1. Remove password2 (not in model)
        2. Hash the password (never store plain text!)
        3. Create user using manager method
        """
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    
    WHY SEPARATE?
    Password change is a different operation than updating profile.
    Requires old password for security.
    """
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        label='Confirm New Password'
    )
    
    def validate_old_password(self, value):
        """
        Check that old password is correct.
        
        WHY: Security! Can't change password without knowing current one.
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value
    
    def validate(self, attrs):
        """Check that new passwords match."""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                'new_password': 'New password fields must match.'
            })
        return attrs
    
    def save(self, **kwargs):
        """Update user's password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
