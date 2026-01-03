"""
Views for pricing app.

Stock price data and historical analysis.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from .models import StockPrice
from stocks.models import Stock
from .serializers import (
    StockPriceSerializer, StockPriceListSerializer,
    PriceRangeRequestSerializer, PriceStatisticsSerializer
)
from accounts.permissions import IsAdminOrReadOnly, CanAccessHistoricalData


class StockPriceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for stock price operations.
    
    PERMISSIONS:
    - Read: All authenticated users
    - Write: Admin only (prices come from background tasks)
    """
    
    queryset = StockPrice.objects.all()
    serializer_class = StockPriceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['stock', 'source']
    ordering = ['-timestamp']  # Required for cursor pagination
    
    def get_queryset(self):
        """
        Optimize queryset with select_related.
        
        WHY: Avoid N+1 queries when serializing stock info.
        """
        return super().get_queryset().select_related('stock')
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get latest prices for all stocks or specific stock.
        
        QUERY PARAMS:
        - symbol: Stock symbol (optional)
        
        CACHING: Results cached for 5 minutes.
        
        ENDPOINT: GET /api/v1/pricing/prices/latest/?symbol=AAPL
        """
        symbol = request.query_params.get('symbol')
        
        if symbol:
            # Get latest price for specific stock
            cache_key = f'latest_price:{symbol.upper()}'
            cached_price = cache.get(cache_key)
            
            if cached_price:
                serializer = StockPriceSerializer(cached_price)
                return Response({
                    'data': serializer.data,
                    'meta': {'cached': True},
                    'errors': []
                })
            
            try:
                stock = Stock.objects.get(symbol__iexact=symbol, is_active=True)
                latest_price = StockPrice.objects.latest_price(stock)
                
                if not latest_price:
                    return Response({
                        'data': None,
                        'meta': {'message': 'No price data available.'},
                        'errors': []
                    })
                
                # Cache for 5 minutes
                cache.set(cache_key, latest_price, 300)
                
                serializer = StockPriceSerializer(latest_price)
                return Response({
                    'data': serializer.data,
                    'meta': {'cached': False},
                    'errors': []
                })
            
            except Stock.DoesNotExist:
                return Response({
                    'data': None,
                    'meta': {},
                    'errors': [{'message': 'Stock not found.'}]
                }, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # Get latest prices for all stocks (expensive!)
            # In production, this should be paginated
            stocks = Stock.objects.active()[:50]  # Limit to 50
            
            latest_prices = []
            for stock in stocks:
                price = StockPrice.objects.latest_price(stock)
                if price:
                    latest_prices.append(price)
            
            serializer = StockPriceListSerializer(latest_prices, many=True)
            return Response({
                'data': serializer.data,
                'meta': {'count': len(latest_prices)},
                'errors': []
            })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanAccessHistoricalData])
    def historical(self, request):
        """
        Get historical prices for a stock within date range.
        
        BUSINESS RULES:
        - Standard users: Last 30 days only
        - Premium/Admin: Unlimited
        
        ENDPOINT: POST /api/v1/pricing/prices/historical/
        BODY: {
            "stock_symbol": "AAPL",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z"
        }
        """
        serializer = PriceRangeRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        stock_symbol = serializer.validated_data['stock_symbol']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        
        try:
            stock = Stock.objects.get(symbol__iexact=stock_symbol, is_active=True)
            
            prices = StockPrice.objects.price_range(stock, start_date, end_date)
            
            # Use lightweight serializer for many data points
            serializer = StockPriceListSerializer(prices, many=True)
            
            return Response({
                'data': serializer.data,
                'meta': {
                    'stock': stock_symbol,
                    'start_date': start_date,
                    'end_date': end_date,
                    'count': len(serializer.data)
                },
                'errors': []
            })
        
        except Stock.DoesNotExist:
            return Response({
                'data': None,
                'meta': {},
                'errors': [{'message': 'Stock not found.'}]
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def statistics(self, request):
        """
        Get price statistics for a period.
        
        Returns min, max, avg, volatility.
        
        ENDPOINT: POST /api/v1/pricing/prices/statistics/
        """
        serializer = PriceRangeRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        stock_symbol = serializer.validated_data['stock_symbol']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        
        try:
            stock = Stock.objects.get(symbol__iexact=stock_symbol, is_active=True)
            
            stats = StockPrice.objects.get_statistics(stock, start_date, end_date)
            count = StockPrice.objects.filter(
                stock=stock,
                timestamp__gte=start_date,
                timestamp__lte=end_date
            ).count()
            
            response_data = {
                'stock_symbol': stock_symbol,
                'period': f'{(end_date - start_date).days} days',
                'start_date': start_date,
                'end_date': end_date,
                'avg_price': stats['avg_price'] or 0,
                'min_price': stats['min_price'] or 0,
                'max_price': stats['max_price'] or 0,
                'volatility': stats['volatility'] or 0,
                'data_points': count
            }
            
            serializer = PriceStatisticsSerializer(response_data)
            
            return Response({
                'data': serializer.data,
                'meta': {},
                'errors': []
            })
        
        except Stock.DoesNotExist:
            return Response({
                'data': None,
                'meta': {},
                'errors': [{'message': 'Stock not found.'}]
            }, status=status.HTTP_404_NOT_FOUND)
