"""
Django admin for stocks app.
"""

from django.contrib import admin
from .models import Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Admin interface for Stock model."""
    
    list_display = ['symbol', 'name', 'exchange', 'currency', 'is_active', 'created_at']
    list_filter = ['exchange', 'currency', 'is_active', 'created_at']
    search_fields = ['symbol', 'name']
    ordering = ['symbol']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('symbol', 'name', 'exchange', 'currency')
        }),
        ('Details', {
            'fields': ('sector', 'industry', 'market_cap')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['activate_stocks', 'deactivate_stocks']
    
    def activate_stocks(self, request, queryset):
        """Bulk activate stocks."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} stock(s) activated.')
    activate_stocks.short_description = 'Activate selected stocks'
    
    def deactivate_stocks(self, request, queryset):
        """Bulk deactivate stocks."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} stock(s) deactivated.')
    deactivate_stocks.short_description = 'Deactivate selected stocks'
