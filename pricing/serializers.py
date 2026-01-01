"""
Serializers for pricing app.

These handle stock price data and historical analysis.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import StockPrice
from stocks.serializers import StockListSerializer


class StockPriceSerializer(serializers.ModelSerializer):
    """
    Serializer for stock prices.
    
    FEATURES:
    - Nested stock info
    - Percentage change calculation
    - Immutable after creation (no updates allowed)
    """
    
    stock_info = StockListSerializer(source='stock', read_only=True)
    percentage_change = serializers.SerializerMethodField()
    
    class Meta:
        model = StockPrice
        fields = [
            'id', 'stock', 'stock_info', 'price', 'volume',
            'source', 'timestamp', 'percentage_change', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_percentage_change(self, obj):
        """
        Calculate percentage change from previous price.
        
        WHY: Users want to see how much the price changed.
        We compare with the previous price record.
        """
        # Get previous price (order by timestamp DESC, skip current)
        previous = StockPrice.objects.filter(
            stock=obj.stock,
            timestamp__lt=obj.timestamp
        ).order_by('-timestamp').first()
        
        if previous:
            return obj.percentage_change(previous)
        
        return 0.0
    
    def validate_timestamp(self, value):
        """
        Validate timestamp is not in the future.
        
        WHY: Can't have price data from the future!
        """
        if value > timezone.now():
            raise serializers.ValidationError(
                'Timestamp cannot be in the future.'
            )
        return value
    
    def validate(self, attrs):
        """
        Additional validation.
        
        WHY: Prevent duplicate prices for same stock+timestamp.
        """
        stock = attrs.get('stock')
        timestamp = attrs.get('timestamp')
        
        if stock and timestamp:
            # Check if price already exists for this stock+timestamp
            exists = StockPrice.objects.filter(
                stock=stock,
                timestamp=timestamp
            ).exists()
            
            if exists:
                raise serializers.ValidationError({
                    'timestamp': 'Price already exists for this stock at this timestamp.'
                })
        
        return attrs


class StockPriceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for price listings.
    
    WHY: When showing price charts, we need many data points.
    Smaller payload = faster response.
    """
    
    class Meta:
        model = StockPrice
        fields = ['price', 'volume', 'timestamp']


class PriceRangeRequestSerializer(serializers.Serializer):
    """
    Serializer for historical price range requests.
    
    WHY: Validates date range parameters.
    Enforces business rules (30-day limit for standard users).
    """
    
    stock_symbol = serializers.CharField(
        required=True,
        help_text='Stock symbol (e.g., AAPL)'
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text='Start date for price range'
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text='End date for price range'
    )
    
    def validate(self, attrs):
        """
        Validate date range.
        
        BUSINESS RULES:
        1. end_date must be after start_date
        2. Standard users: max 30 days
        3. Premium/Admin: unlimited
        """
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date') or timezone.now()
        
        # Default to last 30 days if no start date
        if not start_date:
            start_date = end_date - timedelta(days=30)
            attrs['start_date'] = start_date
        
        # Validate date order
        if start_date >= end_date:
            raise serializers.ValidationError({
                'start_date': 'Start date must be before end date.'
            })
        
        # Check date range limit for non-premium users
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_tier = request.user.profile.account_tier
            
            if user_tier == 'STANDARD':
                max_days = 30
                date_diff = (end_date - start_date).days
                
                if date_diff > max_days:
                    raise serializers.ValidationError({
                        'start_date': f'Standard users can access up to {max_days} days of historical data. '
                                    'Upgrade to Premium for unlimited access.'
                    })
        
        attrs['end_date'] = end_date
        return attrs


class PriceStatisticsSerializer(serializers.Serializer):
    """
    Serializer for price statistics response.
    
    WHY: Standardized format for analytics data.
    """
    
    stock_symbol = serializers.CharField()
    period = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    
    avg_price = serializers.DecimalField(max_digits=15, decimal_places=4)
    min_price = serializers.DecimalField(max_digits=15, decimal_places=4)
    max_price = serializers.DecimalField(max_digits=15, decimal_places=4)
    volatility = serializers.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text='Standard deviation of prices'
    )
    
    data_points = serializers.IntegerField(help_text='Number of price records')
