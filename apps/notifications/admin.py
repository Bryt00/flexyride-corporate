from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from notifications.models import Notification, WebPushSubscription, NotificationCampaign


@admin.register(NotificationCampaign)
class NotificationCampaignAdmin(ModelAdmin):
    list_display = (
        'title', 'channel_badge', 'target_audience_badge',
        'status_badge', 'delivery_progress', 'sent_at', 'created_at'
    )
    list_filter = ('channel', 'target_audience', 'status', 'created_at')
    search_fields = ('title', 'message_body')
    readonly_fields = (
        'total_recipients', 'successful_count', 'failed_count',
        'sent_at', 'error_summary', 'created_at', 'updated_at'
    )
    fieldsets = (
        ('Campaign Strategy', {
            'fields': ('title', 'channel', 'target_audience', 'status')
        }),
        ('Message Content & Call to Action', {
            'fields': ('message_body', 'action_button_text', 'action_url'),
            'description': 'You can use dynamic merge tags: {{name}}, {{company}}, {{date}} in the message body.'
        }),
        ('Dispatch Metrics & Diagnostics', {
            'fields': (
                'total_recipients', 'successful_count', 'failed_count',
                'sent_at', 'error_summary', 'created_by', 'created_at', 'updated_at'
            )
        }),
    )
    actions = ['dispatch_selected_campaigns', 'send_test_to_self']

    @admin.display(description="Channel")
    def channel_badge(self, obj):
        colors = {
            'EMAIL': 'background-color: rgba(59, 130, 246, 0.15); color: #60a5fa;',
            'SMS': 'background-color: rgba(16, 185, 129, 0.15); color: #34d399;',
            'PUSH': 'background-color: rgba(245, 158, 11, 0.15); color: #fbbf24;',
            'EMAIL_AND_SMS': 'background-color: rgba(168, 85, 247, 0.15); color: #c084fc;',
            'ALL': 'background-color: rgba(236, 72, 153, 0.15); color: #f472b6;',
        }
        style = colors.get(obj.channel, 'background-color: rgba(148, 163, 184, 0.15); color: #94a3b8;')
        return format_html(
            '<span style="padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; {}">{}</span>',
            style, obj.get_channel_display()
        )

    @admin.display(description="Audience")
    def target_audience_badge(self, obj):
        return format_html(
            '<span style="font-size: 12px; font-weight: 600; color: #e2e8f0;">{}</span>',
            obj.get_target_audience_display()
        )

    @admin.display(description="Status")
    def status_badge(self, obj):
        badge_styles = {
            'DRAFT': 'background-color: rgba(148, 163, 184, 0.15); color: #94a3b8;',
            'QUEUED': 'background-color: rgba(245, 158, 11, 0.15); color: #fbbf24;',
            'SENDING': 'background-color: rgba(59, 130, 246, 0.15); color: #60a5fa;',
            'SENT': 'background-color: rgba(16, 185, 129, 0.15); color: #34d399;',
            'FAILED': 'background-color: rgba(239, 68, 68, 0.15); color: #f87171;',
            'CANCELLED': 'background-color: rgba(100, 116, 139, 0.15); color: #64748b;',
        }
        style = badge_styles.get(obj.status, 'background-color: rgba(148, 163, 184, 0.15); color: #94a3b8;')
        return format_html(
            '<span style="padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; {}">{}</span>',
            style, obj.get_status_display()
        )

    @admin.display(description="Delivered / Target")
    def delivery_progress(self, obj):
        if obj.total_recipients == 0:
            return format_html('<span style="color: #64748b;">Not sent yet</span>')
        pct = int((obj.successful_count / obj.total_recipients) * 100) if obj.total_recipients else 0
        return format_html(
            '<span style="font-weight: 700; color: #10b981;">{}/{}</span> <span style="color: #94a3b8; font-size: 11px;">({}%)</span>',
            obj.successful_count, obj.total_recipients, pct
        )

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="🚀 Send Selected Campaigns Now (Bulk Broadcast)")
    def dispatch_selected_campaigns(self, request, queryset):
        count = 0
        for campaign in queryset:
            if campaign.status in (NotificationCampaign.Status.DRAFT, NotificationCampaign.Status.FAILED):
                campaign.dispatch(async_mode=True)
                count += 1
        self.message_user(request, f"Dispatched {count} campaign(s) to the background queue.")

    @admin.action(description="🧪 Send Test Preview to Current Admin (Self)")
    def send_test_to_self(self, request, queryset):
        from notifications import tasks
        from django.utils import timezone
        for campaign in queryset:
            # Create a test copy for admin
            test_camp = NotificationCampaign(
                title=f"[TEST PREVIEW] {campaign.title}",
                channel=campaign.channel,
                target_audience=NotificationCampaign.TargetAudience.ALL_USERS,
                message_body=campaign.message_body,
                action_url=campaign.action_url,
                action_button_text=campaign.action_button_text,
                created_by=request.user
            )
            # Override recipients to only current user
            def test_recipients():
                return [{
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email,
                    'phone': getattr(getattr(request.user, 'employee', None), 'phone', '') or '',
                    'company': 'FlexyRide Headquarters',
                    'user': request.user
                }]
            test_camp.get_recipients = test_recipients
            tasks.run_campaign_dispatch(campaign.pk)
        self.message_user(request, f"Sent preview broadcast for {queryset.count()} campaign(s) to {request.user.email}.")


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


