"""
Serializers for stocks app.

These handle stock master data serialization.
Price serializers are in pricing app.
"""

from rest_framework import serializers
from .models import Stock


class StockSerializer(serializers.ModelSerializer):
    """
    Serializer for Stock model.
    
    FEATURES:
    - Full CRUD operations
    - Validation for symbol (uppercase, no spaces)
    - Read-only computed fields
    """
    
    latest_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = [
            'id', 'symbol', 'name', 'exchange', 'currency',
            'sector', 'industry', 'market_cap', 'is_active',
            'latest_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_latest_price(self, obj):
        """
        Get latest price for the stock.
        
        WHY SerializerMethodField?
        This field doesn't exist in the model.
        We compute it dynamically using the pricing app.
        
        PERFORMANCE NOTE:
        This causes N+1 queries if listing many stocks.
        Use select_related/prefetch_related in the view.
        """
        from pricing.models import StockPrice
        
        latest = StockPrice.objects.latest_price(obj)
        if latest:
            return {
                'price': str(latest.price),
                'timestamp': latest.timestamp,
                'source': latest.source
            }
        return None
    
    def validate_symbol(self, value):
        """
        Validate stock symbol format.
        
        WHY: Stock symbols are typically uppercase with no spaces.
        Enforcing this ensures data consistency.
        """
        # Convert to uppercase
        value = value.upper().strip()
        
        # Check for invalid characters
        if not value.replace('.', '').replace('-', '').isalnum():
            raise serializers.ValidationError(
                'Symbol can only contain letters, numbers, dots, and hyphens.'
            )
        
        return value
    
    def validate(self, attrs):
        """
        Additional validation.
        
        WHY: Some validations need multiple fields.
        """
        # Ensure symbol is unique (case-insensitive)
        symbol = attrs.get('symbol', '').upper()
        if symbol:
            queryset = Stock.objects.filter(symbol__iexact=symbol)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'symbol': 'A stock with this symbol already exists.'
                })
        
        return attrs


class StockListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for stock listings.
    
    WHY SEPARATE?
    When listing many stocks, we don't need all fields.
    This improves performance by reducing data transfer and serialization time.
    """
    
    class Meta:
        model = Stock
        fields = ['id', 'symbol', 'name', 'exchange', 'currency']


class StockSearchSerializer(serializers.Serializer):
    """
    Serializer for stock search requests.
    
    WHY: Validates search parameters.
    """
    
    query = serializers.CharField(
        required=True,
        min_length=1,
        max_length=100,
        help_text='Search by symbol or name'
    )
    exchange = serializers.ChoiceField(
        choices=Stock.EXCHANGE_CHOICES,
        required=False,
        help_text='Filter by exchange'
    )
