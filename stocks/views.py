"""
Views for stocks app.

Stock master data management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from .models import Stock
from .serializers import StockSerializer, StockListSerializer, StockSearchSerializer
from accounts.permissions import IsAdminOrReadOnly


class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Stock CRUD operations.
    
    PERMISSIONS:
    - Read: All authenticated users
    - Write: Admin only
    
    WHY QUERYSET OPTIMIZATION?
    queryset() method allows us to optimize queries differently per action.
    
    ENDPOINTS:
    - GET /api/v1/stocks/stocks/ - List stocks
    - POST /api/v1/stocks/stocks/ - Create stock (admin only)
    - GET /api/v1/stocks/stocks/{id}/ - Get stock detail
    - PUT /api/v1/stocks/stocks/{id}/ - Update stock (admin only)
    - DELETE /api/v1/stocks/stocks/{id}/ - Soft delete stock (admin only)
    """
    
    queryset = Stock.objects.active()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    search_fields = ['symbol', 'name']
    filterset_fields = ['exchange', 'currency', 'sector']
    ordering = ['symbol']  # Required for cursor pagination
    
    def get_serializer_class(self):
        """Use lightweight serializer for list action."""
        if self.action == 'list':
            return StockListSerializer
        return StockSerializer
    
    def get_queryset(self):
        """
        Optimize queryset based on action.
        
        WHY: List doesn't need latest prices, detail does.
        """
        queryset = super().get_queryset()
        
        # For list view, don't fetch prices
        if self.action == 'list':
            return queryset.only('id', 'symbol', 'name', 'exchange', 'currency')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search stocks by symbol or name.
        
        WHY CUSTOM ENDPOINT?
        More user-friendly than filter parameters.
        
        ENDPOINT: GET /api/v1/stocks/stocks/search/?query=AAPL
        """
        serializer = StockSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        exchange = serializer.validated_data.get('exchange')
        
        # Use custom manager method
        stocks = Stock.objects.search(query)
        
        if exchange:
            stocks = stocks.filter(exchange=exchange)
        
        # Limit results for performance
        stocks = stocks[:20]
        
        serializer = StockListSerializer(stocks, many=True)
        return Response({
            'data': serializer.data,
            'meta': {
                'count': len(serializer.data),
                'query': query
            },
            'errors': []
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrReadOnly])
    def deactivate(self, request, pk=None):
        """
        Soft delete stock.
        
        WHY: Keep historical data but hide from active stocks.
        
        ENDPOINT: POST /api/v1/stocks/stocks/{id}/deactivate/
        """
        stock = self.get_object()
        stock.soft_delete()
        
        # Invalidate cache
        cache_key = f'latest_price:{stock.symbol}'
        cache.delete(cache_key)
        
        return Response({
            'data': None,
            'meta': {'message': f'Stock {stock.symbol} deactivated successfully.'},
            'errors': []
        })
    
    @action(detail=False, methods=['get'])
    def exchanges(self, request):
        """
        Get list of available exchanges.
        
        WHY: Helps clients build filter dropdowns.
        
        ENDPOINT: GET /api/v1/stocks/stocks/exchanges/
        """
        exchanges = [
            {'code': code, 'name': name}
            for code, name in Stock.EXCHANGE_CHOICES
        ]
        
        return Response({
            'data': exchanges,
            'meta': {},
            'errors': []
        })
