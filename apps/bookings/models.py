import uuid
from django.db import models
from django.conf import settings
from bookings.validators import validate_booking_request


class TransportationRequest(models.Model):
    class InternalApprovalStatus(models.TextChoices):
        NOT_REQUIRED = 'NOT_REQUIRED', 'Not Required'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Internal Approval'
        APPROVED = 'APPROVED', 'Approved by Company'
        REJECTED = 'REJECTED', 'Rejected by Company'

    class JourneyType(models.TextChoices):
        ONE_WAY = 'ONE_WAY', 'One-Way Journey'
        RETURN = 'RETURN', 'Return Journey'
        HOURLY = 'HOURLY', 'Hourly Hire'
        FULL_DAY = 'FULL_DAY', 'Full-Day Hire'
        MULTI_DAY = 'MULTI_DAY', 'Multi-Day Hire'
        MULTI_VEHICLE = 'MULTI_VEHICLE', 'Multiple Vehicles'
        RECURRING = 'RECURRING', 'Recurring Transportation'
        AIRPORT_TRANSFER = 'AIRPORT_TRANSFER', 'Airport Transfer'
        AIRPORT_MEET_GREET = 'AIRPORT_MEET_GREET', 'Airport Meet & Greet'
        EVENT = 'EVENT', 'Event / Conference Transportation'

    class BookingStatus(models.TextChoices):
        REQUEST_SUBMITTED = 'REQUEST_SUBMITTED', 'Request Submitted'
        AWAITING_INTERNAL_APPROVAL = 'AWAITING_INTERNAL_APPROVAL', 'Awaiting Internal Approval'
        APPROVED_BY_COMPANY = 'APPROVED_BY_COMPANY', 'Approved by Company'
        REJECTED_BY_COMPANY = 'REJECTED_BY_COMPANY', 'Rejected by Company'
        RECEIVED_BY_FLEXYRIDE = 'RECEIVED_BY_FLEXYRIDE', 'Received by FlexyRide'
        BEING_ARRANGED = 'BEING_ARRANGED', 'Being Arranged'
        QUOTE_AVAILABLE = 'QUOTE_AVAILABLE', 'Quote Available'
        AWAITING_CUSTOMER_ACCEPTANCE = 'AWAITING_CUSTOMER_ACCEPTANCE', 'Awaiting Customer Acceptance'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        ASSIGNED = 'ASSIGNED', 'Driver/Vehicle Assigned'
        DRIVER_EN_ROUTE = 'DRIVER_EN_ROUTE', 'Driver En Route'
        DRIVER_ARRIVED = 'DRIVER_ARRIVED', 'Driver Arrived'
        PASSENGER_ONBOARD = 'PASSENGER_ONBOARD', 'Passenger Onboard'
        TRIP_IN_PROGRESS = 'TRIP_IN_PROGRESS', 'Trip In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PriorityLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        STANDARD = 'STANDARD', 'Standard'
        URGENT = 'URGENT', 'Urgent'

    request_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        help_text="Human readable unique request reference, e.g. FRC-2026-00001"
    )
    customer = models.ForeignKey(
        'accounts.CorporateCustomer',
        on_delete=models.CASCADE,
        related_name='requests'
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_requests'
    )
    internal_approval_status = models.CharField(
        max_length=30,
        choices=InternalApprovalStatus.choices,
        default=InternalApprovalStatus.NOT_REQUIRED
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    internal_rejection_reason = models.TextField(blank=True, null=True)

    journey_type = models.CharField(
        max_length=30,
        choices=JourneyType.choices,
        default=JourneyType.ONE_WAY
    )

    # Priority & Reference (US-05, US-06)
    priority_level = models.CharField(
        max_length=20,
        choices=PriorityLevel.choices,
        default=PriorityLevel.STANDARD,
        help_text="Urgency level of this request."
    )
    customer_reference = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Customer's internal PO or reference number."
    )

    # Location details
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_address = models.TextField()
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Schedule details
    departure_datetime = models.DateTimeField()
    return_datetime = models.DateTimeField(null=True, blank=True)
    duration_hours = models.PositiveIntegerField(null=True, blank=True)

    # Flight details (for airport transfers)
    flight_number = models.CharField(max_length=50, blank=True, null=True)
    airline = models.CharField(max_length=100, blank=True, null=True)
    flight_datetime = models.DateTimeField(null=True, blank=True)
    airport_name = models.CharField(max_length=255, blank=True, null=True)

    # Requirements & Capacity
    requested_vehicle_category = models.CharField(
        max_length=30,
        choices=models.TextChoices('Category', 'SEDAN EXECUTIVE SUV VAN MINIBUS COASTER_BUS LUXURY').choices,
        default='SEDAN'
    )
    vehicles_requested_count = models.PositiveIntegerField(default=1)
    passenger_count = models.PositiveIntegerField(default=1)
    luggage_requirements = models.TextField(blank=True, null=True)
    accessibility_required = models.BooleanField(default=False)
    child_seats_count = models.PositiveIntegerField(default=0)
    executive_vehicle_required = models.BooleanField(default=False)
    additional_stops_notes = models.TextField(blank=True, null=True)

    # Distance estimation (US-40)
    estimated_distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Estimated journey distance in kilometres."
    )

    # Cancellation policy (US-20)
    cancellation_policy_tier = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Which cancellation policy tier applies to this booking."
    )

    # Overall Lifecycle Status
    booking_status = models.CharField(
        max_length=35,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUEST_SUBMITTED
    )

    # Broker Assignment
    assigned_broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_corporate_bookings'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def clean(self):
        validate_booking_request(self)

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = f"FRC-{uuid.uuid4().hex[:8].upper()}"
        
        # Timeline audit log on status change
        if self.pk:
            old_inst = TransportationRequest.objects.filter(pk=self.pk).first()
            if old_inst and old_inst.booking_status != self.booking_status:
                from feedback.models import BookingTimeline
                BookingTimeline.objects.create(
                    request=self,
                    action_type='STATUS_CHANGED',
                    previous_status=old_inst.booking_status,
                    new_status=self.booking_status,
                    description=f"Booking status changed from {old_inst.get_booking_status_display()} to {self.get_booking_status_display()}"
                )

        super().save(*args, **kwargs)

    def __str__(self):
        cust_name = self.customer.company_name if hasattr(self, 'customer') and self.customer else "Pending Customer"
        return f"{self.request_number} - {cust_name} [{self.get_booking_status_display()}]"

    def get_service_type_display(self):
        """Backward-compatible alias for get_journey_type_display."""
        return self.get_journey_type_display()

    @property
    def service_type(self):
        """Backward-compatible alias for journey_type."""
        return self.journey_type

    @property
    def billed_amount(self):
        """Returns the final customer price or paid amount, or a standard estimate if 0/missing in Ghana Cedis (GHS)."""
        from decimal import Decimal
        payment = self.payments.filter(status='SUCCESSFUL').first() or self.payments.first()
        if payment and payment.amount > 0:
            return payment.amount
        quote = self.customer_quotes.first()
        if quote and quote.final_customer_price > 0:
            return quote.final_customer_price
        
        # Authentic corporate fare estimate in Ghana Cedis (GHS) based on distance and vehicle category
        dist = float(self.estimated_distance_km or 25.0)
        rates = {
            'SEDAN': 18.0,
            'EXECUTIVE': 28.0,
            'SUV': 35.0,
            'VAN': 42.0,
            'MINIBUS': 55.0,
            'COASTER_BUS': 85.0,
            'LUXURY': 75.0
        }
        rate = rates.get(self.requested_vehicle_category, 22.0)
        base = max(150.0, dist * rate)
        return Decimal(str(round(base, 2)))


class PassengerInfo(models.Model):
    request = models.ForeignKey(
        TransportationRequest,
        on_delete=models.CASCADE,
        related_name='passengers'
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    is_primary = models.BooleanField(default=True)
    tracking_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique access token allowing passenger tracking without account registration."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"


class VehicleAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = 'ASSIGNED', 'Assigned'
        EN_ROUTE = 'EN_ROUTE', 'En Route'
        ARRIVED = 'ARRIVED', 'Arrived'
        PASSENGER_ONBOARD = 'PASSENGER_ONBOARD', 'Passenger Onboard'
        TRIP_IN_PROGRESS = 'TRIP_IN_PROGRESS', 'Trip In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REPLACED = 'REPLACED', 'Replaced'

    request = models.ForeignKey(
        TransportationRequest,
        on_delete=models.CASCADE,
        related_name='vehicle_assignments'
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle',
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    driver = models.ForeignKey(
        'fleet.Driver',
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.ASSIGNED
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    replacement_reason = models.TextField(blank=True, null=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.request.request_number} -> {self.vehicle.registration_number} / {self.driver.full_name}"


class RecurringSchedule(models.Model):
    class Frequency(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        CUSTOM = 'CUSTOM', 'Custom Schedule'

    request = models.ForeignKey(
        TransportationRequest,
        on_delete=models.CASCADE,
        related_name='recurring_schedules'
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.WEEKLY
    )
    days_of_week = models.CharField(
        max_length=50,
        help_text="Comma separated days, e.g. MON,WED,FRI"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"Recurring Schedule for {self.request.request_number} ({self.frequency})"


class CancellationRequest(models.Model):
    """Tracks cancellation requests with fee/refund logic (US-19, US-20, US-21, US-99, US-100)."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    request = models.ForeignKey(
        TransportationRequest,
        on_delete=models.CASCADE,
        related_name='cancellation_requests'
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cancellation_requests'
    )
    reason = models.TextField(help_text="Reason for cancellation.")
    cancellation_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Fee charged for cancellation based on policy tier."
    )
    fee_waived = models.BooleanField(
        default=False,
        help_text="Whether the cancellation fee has been waived by FlexyRide."
    )
    refund_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Amount refunded to customer."
    )
    policy_applied = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Name/tier of cancellation policy applied."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"Cancellation for {self.request.request_number} [{self.get_status_display()}]"


