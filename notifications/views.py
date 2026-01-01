"""
Views for notifications app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import PriceAlert, Notification
from .serializers import (
    PriceAlertSerializer, PriceAlertListSerializer,
    NotificationSerializer, MarkNotificationReadSerializer,
    CreatePriceAlertSerializer
)
from accounts.permissions import IsOwnerOrAdmin


class PriceAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for price alert operations."""
    
    serializer_class = PriceAlertSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """Users only see their own alerts."""
        return PriceAlert.objects.filter(user=self.request.user).select_related('stock')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PriceAlertListSerializer
        elif self.action == 'create':
            return CreatePriceAlertSerializer
        return PriceAlertSerializer
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an alert."""
        alert = self.get_object()
        alert.is_active = True
        alert.save(update_fields=['is_active'])
        
        return Response({
            'data': None,
            'meta': {'message': 'Alert activated.'},
            'errors': []
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an alert."""
        alert = self.get_object()
        alert.is_active = False
        alert.save(update_fields=['is_active'])
        
        return Response({
            'data': None,
            'meta': {'message': 'Alert deactivated.'},
            'errors': []
        })


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for notifications (read-only)."""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """Users only see their own notifications."""
        return Notification.objects.filter(user=self.request.user).select_related('alert')
    
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark notifications as read."""
        serializer = MarkNotificationReadSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        notifications = serializer.validated_data['notification_ids']
        
        for notification in notifications:
            notification.mark_as_read()
        
        return Response({
            'data': None,
            'meta': {'message': f'{len(notifications)} notifications marked as read.'},
            'errors': []
        })
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications."""
        notifications = self.get_queryset().filter(read_at__isnull=True)
        serializer = self.get_serializer(notifications, many=True)
        
        return Response({
            'data': serializer.data,
            'meta': {'count': len(serializer.data)},
            'errors': []
        })
