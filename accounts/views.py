"""
Views for accounts app.

WHY VIEWSETS?
ViewSets group related views together:
- list() - GET /users/
- retrieve() - GET /users/{id}/
- create() - POST /users/
- update() - PUT /users/{id}/
- destroy() - DELETE /users/{id}/

DRF automatically generates these from a ViewSet.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from .models import User, Profile
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    ProfileSerializer, ChangePasswordSerializer
)
from .permissions import IsOwnerOrAdmin


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User CRUD operations.
    
    WHY MODELVIEWSET?
    Provides all CRUD operations automatically.
    We just configure queryset, serializer, and permissions.
    
    ENDPOINTS:
    - GET /api/v1/accounts/users/ - List users (admin only)
    - POST /api/v1/accounts/users/ - Create user (public - registration)
    - GET /api/v1/accounts/users/{id}/ - Get user detail
    - PUT /api/v1/accounts/users/{id}/ - Update user
    - DELETE /api/v1/accounts/users/{id}/ - Delete user (soft delete)
    """
    
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [IsOwnerOrAdmin]
    ordering = ['id']  # Required for cursor pagination
    
    def get_serializer_class(self):
        """
        Use different serializers for different actions.
        
        WHY: Registration needs password, profile view doesn't.
        """
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserSerializer
    
    def get_permissions(self):
        """
        Different permissions for different actions.
        
        WHY: Anyone can register, but only owner can view/edit profile.
        """
        if self.action == 'create':
            # Registration is public
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        User registration.
        
        WHY @transaction.atomic?
        If user creation fails, profile won't be created (rolled back).
        Ensures data consistency.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Return user with profile info
        return Response(
            {
                'data': UserSerializer(user).data,
                'meta': {
                    'message': 'User registered successfully. You can now login.'
                },
                'errors': []
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current user's profile.
        
        WHY CUSTOM ACTION?
        Common pattern: GET /users/me/ instead of /users/{id}/
        Users don't need to know their own ID.
        
        ENDPOINT: GET /api/v1/accounts/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response({
            'data': serializer.data,
            'meta': {},
            'errors': []
        })
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """
        Update current user's profile.
        
        ENDPOINT: PUT /api/v1/accounts/users/update_profile/
        """
        serializer = ProfileSerializer(
            request.user.profile,
            data=request.data,
            partial=(request.method == 'PATCH'),
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'data': serializer.data,
            'meta': {'message': 'Profile updated successfully.'},
            'errors': []
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change user password.
        
        WHY SEPARATE ENDPOINT?
        Password change is a sensitive operation.
        Requires old password for security.
        
        ENDPOINT: POST /api/v1/accounts/users/change_password/
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'data': None,
            'meta': {'message': 'Password changed successfully.'},
            'errors': []
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdmin])
    def deactivate(self, request, pk=None):
        """
        Soft delete user account.
        
        WHY SOFT DELETE?
        - Preserve data integrity
        - Allow account recovery
        - Comply with audit requirements
        
        ENDPOINT: POST /api/v1/accounts/users/{id}/deactivate/
        """
        user = self.get_object()
        user.soft_delete()
        
        return Response({
            'data': None,
            'meta': {'message': 'Account deactivated successfully.'},
            'errors': []
        }, status=status.HTTP_204_NO_CONTENT)
