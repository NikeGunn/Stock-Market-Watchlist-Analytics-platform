"""
Serializers for watchlists app.

These handle watchlist and watchlist item serialization.
"""

from rest_framework import serializers
from .models import Watchlist, WatchlistItem
from stocks.serializers import StockListSerializer


class WatchlistItemSerializer(serializers.ModelSerializer):
    """
    Serializer for watchlist items.
    
    FEATURES:
    - Nested stock information
    - Latest price included
    - Alert threshold configuration
    """
    
    stock_info = StockListSerializer(source='stock', read_only=True)
    latest_price = serializers.SerializerMethodField()
    
    class Meta:
        model = WatchlistItem
        fields = [
            'id', 'watchlist', 'stock', 'stock_info',
            'alert_thresholds', 'latest_price', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_latest_price(self, obj):
        """
        Get latest price for the stock.
        
        WHY: Users viewing watchlist want to see current prices.
        """
        latest = obj.get_latest_price()
        if latest:
            return {
                'price': str(latest.price),
                'timestamp': latest.timestamp
            }
        return None
    
    def validate_alert_thresholds(self, value):
        """
        Validate alert thresholds JSON structure.
        
        WHY: We store flexible JSON, but need to validate structure.
        Expected format:
        {
            "price_above": 150.00,
            "price_below": 100.00,
            "percent_change": 5.0
        }
        """
        if not isinstance(value, dict):
            return value
        
        # Validate numeric values
        for key in ['price_above', 'price_below', 'percent_change']:
            if key in value:
                try:
                    float(value[key])
                except (TypeError, ValueError):
                    raise serializers.ValidationError({
                        key: 'Must be a valid number.'
                    })
        
        # Validate logical consistency
        if 'price_above' in value and 'price_below' in value:
            if float(value['price_above']) <= float(value['price_below']):
                raise serializers.ValidationError(
                    'price_above must be greater than price_below.'
                )
        
        return value


class WatchlistSerializer(serializers.ModelSerializer):
    """
    Serializer for watchlists.
    
    FEATURES:
    - Nested watchlist items
    - Stock count
    - User ownership validation
    """
    
    items = WatchlistItemSerializer(many=True, read_only=True)
    stock_count = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Watchlist
        fields = [
            'id', 'user', 'user_email', 'name', 'is_default',
            'items', 'stock_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_stock_count(self, obj):
        """Get number of stocks in watchlist."""
        return obj.get_stock_count()
    
    def validate_name(self, value):
        """
        Validate watchlist name is unique for this user.
        
        WHY: Users shouldn't have multiple watchlists with the same name.
        """
        request = self.context.get('request')
        if request and request.user:
            # Check if name already exists for this user
            queryset = Watchlist.objects.filter(user=request.user, name=value)
            
            # Exclude current instance if updating
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    'You already have a watchlist with this name.'
                )
        
        return value
    
    def create(self, validated_data):
        """
        Create watchlist with current user as owner.
        
        WHY OVERRIDE?
        User is set from request, not from client input.
        This prevents users from creating watchlists for other users.
        """
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class WatchlistListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for watchlist listings.
    
    WHY: When listing watchlists, we don't need full item details.
    """
    
    stock_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Watchlist
        fields = ['id', 'name', 'is_default', 'stock_count', 'created_at']
    
    def get_stock_count(self, obj):
        """Get stock count efficiently."""
        return obj.items.count()


class AddStockToWatchlistSerializer(serializers.Serializer):
    """
    Serializer for adding stocks to watchlist.
    
    WHY SEPARATE?
    Different from creating WatchlistItem directly.
    Provides better API for bulk operations.
    """
    
    stock_symbol = serializers.CharField(
        required=True,
        help_text='Stock symbol to add (e.g., AAPL)'
    )
    alert_thresholds = serializers.JSONField(
        required=False,
        default=dict,
        help_text='Optional alert thresholds'
    )
    
    def validate_stock_symbol(self, value):
        """Validate stock exists."""
        from stocks.models import Stock
        
        try:
            stock = Stock.objects.get(symbol__iexact=value, is_active=True)
            return stock
        except Stock.DoesNotExist:
            raise serializers.ValidationError(
                f'Stock with symbol "{value}" not found.'
            )
    
    def validate(self, attrs):
        """
        Validate stock not already in watchlist.
        
        WHY: Prevent duplicate stocks in same watchlist.
        """
        watchlist = self.context.get('watchlist')
        stock = attrs.get('stock_symbol')  # This is now a Stock object
        
        if watchlist and stock:
            if WatchlistItem.objects.filter(watchlist=watchlist, stock=stock).exists():
                raise serializers.ValidationError({
                    'stock_symbol': 'This stock is already in your watchlist.'
                })
        
        return attrs


class BulkAddStocksSerializer(serializers.Serializer):
    """
    Serializer for adding multiple stocks at once.
    
    WHY: Better UX - users can add many stocks in one request.
    """
    
    stock_symbols = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=50,  # Limit bulk operations
        help_text='List of stock symbols to add'
    )
    
    def validate_stock_symbols(self, value):
        """
        Validate all stocks exist.
        
        WHY: Atomic operation - all succeed or all fail.
        """
        from stocks.models import Stock
        
        # Convert to uppercase
        symbols = [s.upper().strip() for s in value]
        
        # Check all exist
        stocks = Stock.objects.filter(symbol__in=symbols, is_active=True)
        found_symbols = set(stock.symbol for stock in stocks)
        
        missing = set(symbols) - found_symbols
        if missing:
            raise serializers.ValidationError(
                f'Stocks not found: {", ".join(missing)}'
            )
        
        return list(stocks)  # Return Stock objects
