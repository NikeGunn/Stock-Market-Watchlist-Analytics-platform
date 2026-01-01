"""
Serializers for notifications app.

These handle price alerts and notifications.
"""

from rest_framework import serializers
from django.utils import timezone
from .models import PriceAlert, Notification
from stocks.serializers import StockListSerializer


class PriceAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for price alerts.
    
    FEATURES:
    - Nested stock info
    - Validation of threshold values
    - User ownership
    """
    
    stock_info = StockListSerializer(source='stock', read_only=True)
    is_triggered = serializers.SerializerMethodField()
    
    class Meta:
        model = PriceAlert
        fields = [
            'id', 'user', 'stock', 'stock_info', 'condition_type',
            'threshold_value', 'one_time', 'is_active', 'is_triggered',
            'triggered_at', 'last_checked_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'triggered_at', 'last_checked_at',
            'created_at', 'updated_at'
        ]
    
    def get_is_triggered(self, obj):
        """Check if alert has been triggered."""
        return obj.triggered_at is not None
    
    def validate_threshold_value(self, value):
        """
        Validate threshold value is positive.
        
        WHY: Negative prices/percentages don't make sense.
        """
        if value <= 0:
            raise serializers.ValidationError(
                'Threshold value must be greater than zero.'
            )
        return value
    
    def validate(self, attrs):
        """
        Additional validation based on condition type.
        
        WHY: Different condition types have different rules.
        """
        condition_type = attrs.get('condition_type')
        threshold_value = attrs.get('threshold_value')
        stock = attrs.get('stock')
        
        # For PERCENT_CHANGE, threshold should be reasonable (e.g., 0-100)
        if condition_type == 'PERCENT_CHANGE' and threshold_value > 100:
            raise serializers.ValidationError({
                'threshold_value': 'Percentage change should be between 0 and 100.'
            })
        
        # Get current price for validation
        if stock:
            from pricing.models import StockPrice
            latest_price = StockPrice.objects.latest_price(stock)
            
            if not latest_price:
                raise serializers.ValidationError({
                    'stock': 'No price data available for this stock.'
                })
            
            # Warn if alert will trigger immediately
            current_price = latest_price.price
            
            if condition_type == 'PRICE_ABOVE' and threshold_value <= current_price:
                # This is just a warning - we still allow it
                pass
            elif condition_type == 'PRICE_BELOW' and threshold_value >= current_price:
                # This is just a warning - we still allow it
                pass
        
        return attrs
    
    def create(self, validated_data):
        """
        Create alert with current user as owner.
        
        WHY: User is set from request context.
        """
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class PriceAlertListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for alert listings.
    """
    
    stock_symbol = serializers.CharField(source='stock.symbol', read_only=True)
    is_triggered = serializers.SerializerMethodField()
    
    class Meta:
        model = PriceAlert
        fields = [
            'id', 'stock_symbol', 'condition_type', 'threshold_value',
            'is_active', 'is_triggered', 'created_at'
        ]
    
    def get_is_triggered(self, obj):
        """Check if alert has been triggered."""
        return obj.triggered_at is not None


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notifications.
    
    FEATURES:
    - Read-only (notifications are system-generated)
    - Related alert info
    - Read status tracking
    """
    
    alert_info = PriceAlertListSerializer(source='alert', read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'alert', 'alert_info', 'notification_type',
            'channel', 'subject', 'message', 'status', 'sent_at',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'alert', 'notification_type', 'channel',
            'subject', 'message', 'status', 'sent_at', 'created_at'
        ]
    
    def get_is_read(self, obj):
        """Check if notification has been read."""
        return obj.read_at is not None


class MarkNotificationReadSerializer(serializers.Serializer):
    """
    Serializer for marking notifications as read.
    """
    
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text='List of notification IDs to mark as read'
    )
    
    def validate_notification_ids(self, value):
        """
        Validate all notifications exist and belong to user.
        
        WHY: Security - users can only mark their own notifications.
        """
        request = self.context.get('request')
        
        notifications = Notification.objects.filter(
            id__in=value,
            user=request.user
        )
        
        if notifications.count() != len(value):
            raise serializers.ValidationError(
                'Some notifications not found or do not belong to you.'
            )
        
        return list(notifications)  # Return Notification objects


class CreatePriceAlertSerializer(serializers.Serializer):
    """
    Convenience serializer for creating price alerts with stock symbol.
    
    WHY: Better API - users send symbol, not stock ID.
    """
    
    stock_symbol = serializers.CharField(
        required=True,
        write_only=True,
        help_text='Stock symbol (e.g., AAPL)'
    )
    condition_type = serializers.ChoiceField(
        choices=PriceAlert.CONDITION_TYPES,
        required=True
    )
    threshold_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=4,
        required=True
    )
    one_time = serializers.BooleanField(default=True)
    
    # Read-only fields for response
    id = serializers.UUIDField(read_only=True)
    stock = serializers.CharField(source='stock.symbol', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
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
    
    def create(self, validated_data):
        """
        Create price alert.
        
        WHY OVERRIDE?
        - Convert stock_symbol to stock object
        - Set user from request
        """
        request = self.context.get('request')
        stock = validated_data.pop('stock_symbol')  # This is now a Stock object
        
        alert = PriceAlert.objects.create(
            user=request.user,
            stock=stock,
            **validated_data
        )
        
        return alert
