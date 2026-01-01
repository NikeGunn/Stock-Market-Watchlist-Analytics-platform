"""
Django admin for pricing app.
"""

from django.contrib import admin
from .models import StockPrice


@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):
    """Admin interface for StockPrice model."""
    
    list_display = ['stock', 'price', 'volume', 'source', 'timestamp', 'created_at']
    list_filter = ['source', 'timestamp', 'created_at']
    search_fields = ['stock__symbol', 'stock__name']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Stock', {
            'fields': ('stock',)
        }),
        ('Price Data', {
            'fields': ('price', 'volume')
        }),
        ('Metadata', {
            'fields': ('source', 'timestamp')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    # Make prices read-only after creation (immutable)
    def has_change_permission(self, request, obj=None):
        """Prices should be immutable once created."""
        return False
