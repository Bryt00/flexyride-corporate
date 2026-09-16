from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class JourneyRating(models.Model):
    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (poor) to 5 (excellent)."
    )
    comments = models.TextField(blank=True, null=True)
    rated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_ratings'
    )
    passenger_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of passenger if rated by passenger without account."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating}/5 for {self.request.request_number}"


class SupportIssue(models.Model):
    class IssueType(models.TextChoices):
        NO_SHOW = 'NO_SHOW', 'Passenger / Driver No-Show'
        DRIVER_DELAY = 'DRIVER_DELAY', 'Driver Delay'
        VEHICLE_CONDITION = 'VEHICLE_CONDITION', 'Vehicle Condition / Spec Mismatch'
        DRIVER_BEHAVIOR = 'DRIVER_BEHAVIOR', 'Driver Conduct'
        BILLING_DISPUTE = 'BILLING_DISPUTE', 'Billing Dispute'
        CANCELLATION_DISPUTE = 'CANCELLATION_DISPUTE', 'Cancellation Dispute'
        OTHER = 'OTHER', 'Other Feedback / Complaint'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        INVESTIGATING = 'INVESTIGATING', 'Under Investigation'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='support_issues'
    )
    issue_type = models.CharField(
        max_length=30,
        choices=IssueType.choices,
        default=IssueType.OTHER
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_support_issues'
    )
    reported_by_passenger = models.BooleanField(default=False)
    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_support_issues'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Issue [{self.get_issue_type_display()}] - {self.request.request_number} [{self.get_status_display()}]"


class InternalBookingNote(models.Model):
    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='internal_notes'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authored_internal_notes'
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Internal Note by {self.author.username} on {self.request.request_number}"


class BookingTimeline(models.Model):
    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='timeline_events'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed the action, or null if system-generated."
    )
    action_type = models.CharField(max_length=100)
    previous_status = models.CharField(max_length=50, blank=True, null=True)
    new_status = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Timeline {self.action_type} for {self.request.request_number} at {self.timestamp}"

