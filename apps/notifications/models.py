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

