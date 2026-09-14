from django.db import models
from django.conf import settings


class Vehicle(models.Model):
    class Category(models.TextChoices):
        SEDAN = 'SEDAN', 'Standard Sedan'
        EXECUTIVE = 'EXECUTIVE', 'Executive Saloon'
        SUV = 'SUV', 'SUV / 4x4'
        VAN = 'VAN', 'Passenger Van'
        MINIBUS = 'MINIBUS', 'Minibus / Shuttle'
        COASTER_BUS = 'COASTER_BUS', 'Coaster Bus'
        LUXURY = 'LUXURY', 'VIP / Luxury Vehicle'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        ASSIGNED = 'ASSIGNED', 'Assigned to Trip'
        MAINTENANCE = 'MAINTENANCE', 'In Maintenance'
        INACTIVE = 'INACTIVE', 'Inactive'

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = 'COMPLIANT', 'Compliant & Approved'
        NON_COMPLIANT = 'NON_COMPLIANT', 'Non-Compliant / Expired'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'

    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    registration_number = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.SEDAN
    )
    seating_capacity = models.PositiveIntegerField(default=4)
    luggage_capacity = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. 3 large suitcases, 2 small bags"
    )
    has_accessibility = models.BooleanField(
        default=False,
        help_text="Wheelchair accessible vehicle."
    )
    has_child_seat = models.BooleanField(
        default=False,
    )
    # Amenities (US-09)
    wifi_available = models.BooleanField(
        default=False,
        help_text="Vehicle has WiFi available."
    )
    water_provided = models.BooleanField(
        default=False,
        help_text="Equipped with child safety seats."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.PENDING_REVIEW
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_available_for_assignment(self):
        return (
            self.status == self.Status.AVAILABLE and
            self.compliance_status == self.ComplianceStatus.COMPLIANT
        )

    def __str__(self):
        return f"{self.make} {self.model} ({self.registration_number}) - {self.get_category_display()}"


class VehiclePhoto(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(upload_to='vehicle_photos/%Y/%m/')
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.vehicle.registration_number}"


class Driver(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        ON_TRIP = 'ON_TRIP', 'On Trip'
        OFF_DUTY = 'OFF_DUTY', 'Off Duty'
        INACTIVE = 'INACTIVE', 'Inactive'

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = 'COMPLIANT', 'Compliant & Approved'
        NON_COMPLIANT = 'NON_COMPLIANT', 'Non-Compliant / Expired'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'

    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='drivers'
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_profile'
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    license_number = models.CharField(max_length=100)
    license_expiry = models.DateField(null=True, blank=True)
    # Driver profile (US-28, US-48)
    photo = models.ImageField(
        upload_to='driver_photos/%Y/%m/', blank=True, null=True,
        help_text="Driver profile photo."
    )
    languages_spoken = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Comma-separated languages (e.g. English,Twi,Ga,Hausa)."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.PENDING_REVIEW
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_available_for_assignment(self):
        return (
            self.status == self.Status.AVAILABLE and
            self.compliance_status == self.ComplianceStatus.COMPLIANT
        )

    def __str__(self):
        return f"{self.full_name} ({self.provider.company_name}) [{self.get_status_display()}]"


class VehicleCategoryRate(models.Model):
    """
    Broker-provided baseline wholesale rate and vehicle specifications schedule.
    Shown on the Provider Portal so transport providers categorize their fleet
    under the agreed broker pricing framework.
    """
    category = models.CharField(
        max_length=30,
        choices=Vehicle.Category.choices,
        unique=True,
        help_text="Standard vehicle category class"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="e.g. SUV / 4x4 (Executive Fleet)"
    )
    description = models.TextField(
        blank=True,
        help_text="Vehicle specifications, passenger class, and standards"
    )
    base_wholesale_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Broker-provided baseline wholesale payout for this category in GHS"
    )
    per_km_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Additional per-km payout guideline in GHS/km"
    )
    daily_charter_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Full-day charter wholesale benchmark in GHS"
    )
    min_seating_capacity = models.PositiveIntegerField(
        default=4,
        help_text="Minimum passenger seating capacity"
    )
    recommended_models = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. Toyota Prado, Pajero, Fortuner"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is actively open for provider listing"
    )
    display_order = models.PositiveIntegerField(
        default=1,
        help_text="Order in dropdowns and pricing schedules"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'category']
        verbose_name = 'Vehicle Category & Pricing Rate'
        verbose_name_plural = 'Vehicle Categories & Pricing Rates'

    def __str__(self):
        return f"{self.display_name} — GHS {self.base_wholesale_rate:,.2f}"

