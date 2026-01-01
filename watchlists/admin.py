"""
Django admin for watchlists app.
"""

from django.contrib import admin
from .models import Watchlist, WatchlistItem


class WatchlistItemInline(admin.TabularInline):
    """Inline admin for watchlist items."""
    model = WatchlistItem
    extra = 0
    fields = ['stock', 'alert_thresholds', 'added_at']
    readonly_fields = ['added_at']


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    """Admin interface for Watchlist model."""
    
    list_display = ['name', 'user', 'is_default', 'stock_count', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name', 'user__email']
    ordering = ['-created_at']
    inlines = [WatchlistItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def stock_count(self, obj):
        """Display stock count in list view."""
        return obj.get_stock_count()
    stock_count.short_description = 'Stocks'


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    """Admin interface for WatchlistItem model."""
    
    list_display = ['watchlist', 'stock', 'has_alerts', 'added_at']
    list_filter = ['added_at']
    search_fields = ['watchlist__name', 'stock__symbol', 'stock__name']
    ordering = ['-added_at']
    
    fieldsets = (
        ('Watchlist Item', {
            'fields': ('watchlist', 'stock')
        }),
        ('Alerts', {
            'fields': ('alert_thresholds',)
        }),
        ('Metadata', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['added_at']
    
    def has_alerts(self, obj):
        """Check if item has alert thresholds configured."""
        return bool(obj.alert_thresholds)
    has_alerts.boolean = True
    has_alerts.short_description = 'Alerts Configured'
