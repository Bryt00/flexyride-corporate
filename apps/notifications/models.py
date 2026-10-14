from typing import TYPE_CHECKING
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """System notifications sent to users and passengers (US-25 through US-30, US-104)."""

    class Channel(models.TextChoices):
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'
        PUSH = 'PUSH', 'Push Notification'
        IN_APP = 'IN_APP', 'In-App Notification'

    class NotificationType(models.TextChoices):
        BOOKING_UPDATE = 'BOOKING_UPDATE', 'Booking Status Update'
        QUOTE_READY = 'QUOTE_READY', 'Quote Ready'
        QUOTE_EXPIRING = 'QUOTE_EXPIRING', 'Quote Expiring Soon'
        PAYMENT_CONFIRMED = 'PAYMENT_CONFIRMED', 'Payment Confirmed'
        DRIVER_ASSIGNED = 'DRIVER_ASSIGNED', 'Driver Assigned'
        DRIVER_EN_ROUTE = 'DRIVER_EN_ROUTE', 'Driver En Route'
        DRIVER_ARRIVED = 'DRIVER_ARRIVED', 'Driver Arrived'
        TRIP_COMPLETED = 'TRIP_COMPLETED', 'Trip Completed'
        CANCELLATION = 'CANCELLATION', 'Booking Cancelled'
        COMPLIANCE_EXPIRY = 'COMPLIANCE_EXPIRY', 'Compliance Document Expiring'
        APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Internal Approval Required'
        CAMPAIGN = 'CAMPAIGN', 'Campaign Broadcast'
        SYSTEM = 'SYSTEM', 'System Notification'

    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications',
        help_text="User recipient. Null if sent to passenger without account."
    )
    passenger_info = models.ForeignKey(
        'bookings.PassengerInfo',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='notifications',
        help_text="Passenger recipient for accountless passengers."
    )
    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.IN_APP
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(
        max_length=15,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    if TYPE_CHECKING:
        def get_notification_type_display(self) -> str: ...
        def get_delivery_status_display(self) -> str: ...

    def __str__(self):
        target = self.recipient or self.passenger_info or "Unknown"
        return f"[{self.get_notification_type_display()}] {self.title} -> {target}"


class WebPushSubscription(models.Model):
    """Stores standard browser push subscriptions (endpoint, p256dh, auth) for free Web Push."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='web_push_subscriptions'
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        owner = self.user.username if self.user else "Anonymous"
        return f"PushSubscription ({owner}) - {self.endpoint[:40]}..."


class NotificationCampaign(models.Model):
    """
    Broadcast campaign manager delivering bulk Email, SMS, and Web Push notifications
    to targeted audiences (Corporate Customers, Transport Providers, Drivers, and Passengers).
    """

    class Channel(models.TextChoices):
        EMAIL = 'EMAIL', 'Email Broadcast'
        SMS = 'SMS', 'SMS Broadcast'
        PUSH = 'PUSH', 'Web Push Notification'
        EMAIL_AND_SMS = 'EMAIL_AND_SMS', 'Email & SMS (Multi-Channel)'
        ALL = 'ALL', 'All Channels (Email, SMS & Web Push)'

    class TargetAudience(models.TextChoices):
        ALL_CUSTOMERS = 'ALL_CUSTOMERS', 'All Corporate Customers & Billing Contacts'
        ALL_PROVIDERS = 'ALL_PROVIDERS', 'All Transport Providers'
        ALL_DRIVERS = 'ALL_DRIVERS', 'All Active Fleet Drivers'
        ACTIVE_PASSENGERS = 'ACTIVE_PASSENGERS', 'All Registered / Recent Passengers'
        ALL_USERS = 'ALL_USERS', 'All Registered Platform Users'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        QUEUED = 'QUEUED', 'Queued'
        SENDING = 'SENDING', 'Sending in Progress'
        SENT = 'SENT', 'Sent Successfully'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    title = models.CharField(
        max_length=255,
        help_text="Internal campaign title / Email subject line"
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.EMAIL,
        help_text="Communication channel(s) for this broadcast."
    )
    target_audience = models.CharField(
        max_length=30,
        choices=TargetAudience.choices,
        default=TargetAudience.ALL_CUSTOMERS,
        help_text="Target recipient segment."
    )
    message_body = models.TextField(
        help_text="Campaign content. Supports template tags like {{name}}, {{company}}, {{date}}."
    )
    action_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional button link / click-through URL for email and push notifications."
    )
    action_button_text = models.CharField(
        max_length=60,
        blank=True,
        default='View in Portal',
        help_text="Call to action button text (for emails & push notifications)."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    total_recipients = models.PositiveIntegerField(default=0)
    successful_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True, default='')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_campaigns'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Broadcast Campaign"
        verbose_name_plural = "Broadcast Campaigns"

    def __str__(self):
        return f"{self.title} [{self.get_channel_display()}] - {self.get_status_display()}"

    def get_recipients(self):
        """Resolves target audience into a list of recipient dictionaries."""
        recipients = []
        seen_keys = set()

        if self.target_audience in (self.TargetAudience.ALL_CUSTOMERS, self.TargetAudience.ALL_USERS):
            from accounts.models import CorporateCustomer, CompanyEmployee
            for c in CorporateCustomer.objects.all():
                email = c.contact_email
                if email and email not in seen_keys:
                    seen_keys.add(email)
                    recipients.append({
                        'name': c.company_name,
                        'email': email,
                        'phone': c.contact_phone or '',
                        'company': c.company_name,
                        'user': None
                    })
            for e in CompanyEmployee.objects.select_related('user', 'company').all():
                email = e.user.email if e.user else ''
                if email and email not in seen_keys:
                    seen_keys.add(email)
                    recipients.append({
                        'name': e.user.get_full_name() or e.user.username,
                        'email': email,
                        'phone': getattr(e.user, 'phone_number', '') or '',
                        'company': e.company.company_name if e.company else '',
                        'user': e.user
                    })

        if self.target_audience in (self.TargetAudience.ALL_PROVIDERS, self.TargetAudience.ALL_USERS):
            from accounts.models import ProviderCompany
            for p in ProviderCompany.objects.all():
                email = p.email
                if email and email not in seen_keys:
                    seen_keys.add(email)
                    recipients.append({
                        'name': p.contact_person or p.company_name,
                        'email': email,
                        'phone': p.phone or '',
                        'company': p.company_name,
                        'user': None
                    })

        if self.target_audience in (self.TargetAudience.ALL_DRIVERS, self.TargetAudience.ALL_USERS):
            from fleet.models import Driver
            for d in Driver.objects.select_related('user', 'provider').all():
                email = d.user.email if (hasattr(d, 'user') and d.user) else ''
                phone = d.phone_number or ''
                key = email or phone
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    recipients.append({
                        'name': d.full_name,
                        'email': email,
                        'phone': phone,
                        'company': d.provider.company_name if d.provider else '',
                        'user': getattr(d, 'user', None)
                    })

        if self.target_audience in (self.TargetAudience.ACTIVE_PASSENGERS, self.TargetAudience.ALL_USERS):
            from bookings.models import PassengerInfo
            for p in PassengerInfo.objects.exclude(email__isnull=True).exclude(email='').values('full_name', 'email', 'phone_number').distinct():
                email = p.get('email')
                if email and email not in seen_keys:
                    seen_keys.add(email)
                    recipients.append({
                        'name': p.get('full_name') or 'Valued Passenger',
                        'email': email,
                        'phone': p.get('phone_number') or '',
                        'company': '',
                        'user': None
                    })

        return recipients

    def dispatch(self, async_mode: bool = True):
        """Enqueues or runs the campaign dispatch logic."""
        from notifications import tasks
        self.status = self.Status.QUEUED
        self.save(update_fields=['status'])
        if async_mode:
            try:
                tasks.dispatch_campaign_task.delay(self.pk)
            except Exception:
                import threading
                threading.Thread(target=tasks.run_campaign_dispatch, args=(self.pk,), daemon=True).start()
        else:
            tasks.run_campaign_dispatch(self.pk)


