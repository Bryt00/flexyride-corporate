from django.contrib import admin
from unfold.admin import ModelAdmin
from notifications.models import Notification, WebPushSubscription


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('title', 'notification_type', 'channel', 'recipient', 'delivery_status', 'sent_at', 'read_at')
    list_filter = ('notification_type', 'channel', 'delivery_status')
    search_fields = ('title', 'message', 'recipient__username', 'request__request_number')
    readonly_fields = ('created_at',)
    raw_id_fields = ('recipient', 'passenger_info', 'request')


@admin.register(WebPushSubscription)
class WebPushSubscriptionAdmin(ModelAdmin):
    list_display = ('user', 'endpoint', 'created_at', 'last_used_at')
    search_fields = ('user__username', 'endpoint')
    readonly_fields = ('created_at', 'last_used_at')
    raw_id_fields = ('user',)

