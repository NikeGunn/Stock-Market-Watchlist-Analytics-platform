"""
Django admin for notifications app.
"""

from django.contrib import admin
from .models import PriceAlert, Notification


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    """Admin interface for PriceAlert model."""
    
    list_display = [
        'user', 'stock', 'condition_type', 'threshold_value',
        'is_active', 'one_time', 'triggered_at', 'created_at'
    ]
    list_filter = ['condition_type', 'is_active', 'one_time', 'created_at']
    search_fields = ['user__email', 'stock__symbol', 'stock__name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Alert Configuration', {
            'fields': ('user', 'stock', 'condition_type', 'threshold_value')
        }),
        ('Behavior', {
            'fields': ('one_time', 'is_active')
        }),
        ('Tracking', {
            'fields': ('triggered_at', 'last_checked_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['triggered_at', 'last_checked_at', 'created_at', 'updated_at']
    
    actions = ['activate_alerts', 'deactivate_alerts']
    
    def activate_alerts(self, request, queryset):
        """Bulk activate alerts."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} alert(s) activated.')
    activate_alerts.short_description = 'Activate selected alerts'
    
    def deactivate_alerts(self, request, queryset):
        """Bulk deactivate alerts."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} alert(s) deactivated.')
    deactivate_alerts.short_description = 'Deactivate selected alerts'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model."""
    
    list_display = [
        'user', 'notification_type', 'channel', 'subject',
        'status', 'sent_at', 'read_at', 'created_at'
    ]
    list_filter = ['notification_type', 'channel', 'status', 'created_at']
    search_fields = ['user__email', 'subject', 'message']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Recipient', {
            'fields': ('user', 'alert')
        }),
        ('Notification', {
            'fields': ('notification_type', 'channel', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'error_message')
        }),
        ('In-App', {
            'fields': ('read_at',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['sent_at', 'created_at']
