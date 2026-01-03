"""
Views for watchlists app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Watchlist, WatchlistItem
from .serializers import (
    WatchlistSerializer, WatchlistListSerializer, WatchlistItemSerializer,
    AddStockToWatchlistSerializer, BulkAddStocksSerializer
)
from accounts.permissions import IsOwnerOrAdmin, CanCreateMultipleWatchlists


class WatchlistViewSet(viewsets.ModelViewSet):
    """ViewSet for watchlist operations."""
    
    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    ordering = ['-created_at']  # Required for cursor pagination
    
    def get_queryset(self):
        """Users only see their own watchlists."""
        return Watchlist.objects.filter(user=self.request.user).prefetch_related('items__stock')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WatchlistListSerializer
        return WatchlistSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), CanCreateMultipleWatchlists()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        """Add stock to watchlist."""
        watchlist = self.get_object()
        serializer = AddStockToWatchlistSerializer(
            data=request.data,
            context={'watchlist': watchlist}
        )
        serializer.is_valid(raise_exception=True)
        
        stock = serializer.validated_data['stock_symbol']
        alert_thresholds = serializer.validated_data.get('alert_thresholds', {})
        
        item = WatchlistItem.objects.create(
            watchlist=watchlist,
            stock=stock,
            alert_thresholds=alert_thresholds
        )
        
        return Response({
            'data': WatchlistItemSerializer(item).data,
            'meta': {'message': f'{stock.symbol} added to watchlist.'},
            'errors': []
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def bulk_add(self, request, pk=None):
        """Bulk add stocks to watchlist."""
        watchlist = self.get_object()
        serializer = BulkAddStocksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        stocks = serializer.validated_data['stock_symbols']
        
        with transaction.atomic():
            items = []
            for stock in stocks:
                item, created = WatchlistItem.objects.get_or_create(
                    watchlist=watchlist,
                    stock=stock
                )
                if created:
                    items.append(item)
            
            return Response({
                'data': {'added': len(items)},
                'meta': {'message': f'{len(items)} stocks added.'},
                'errors': []
            })
    
    @action(detail=True, methods=['delete'])
    def remove_stock(self, request, pk=None):
        """Remove stock from watchlist."""
        watchlist = self.get_object()
        stock_symbol = request.query_params.get('symbol')
        
        if not stock_symbol:
            return Response({
                'data': None,
                'meta': {},
                'errors': [{'message': 'symbol parameter is required.'}]
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from stocks.models import Stock
            stock = Stock.objects.get(symbol__iexact=stock_symbol)
            item = WatchlistItem.objects.get(watchlist=watchlist, stock=stock)
            item.delete()
            
            return Response({
                'data': None,
                'meta': {'message': f'{stock_symbol} removed from watchlist.'},
                'errors': []
            })
        except (Stock.DoesNotExist, WatchlistItem.DoesNotExist):
            return Response({
                'data': None,
                'meta': {},
                'errors': [{'message': 'Stock not found in watchlist.'}]
            }, status=status.HTTP_404_NOT_FOUND)


class WatchlistItemViewSet(viewsets.ModelViewSet):
    """ViewSet for watchlist item operations."""
    
    serializer_class = WatchlistItemSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    ordering = ['-created_at']  # Required for cursor pagination
    
    def get_queryset(self):
        """Users only see their own watchlist items."""
        return WatchlistItem.objects.filter(
            watchlist__user=self.request.user
        ).select_related('watchlist', 'stock')
