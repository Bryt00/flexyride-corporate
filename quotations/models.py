from django.db import models
from django.conf import settings


class ProviderQuoteRequest(models.Model):
    class Status(models.TextChoices):
        SENT = 'SENT', 'Request Sent to Provider'
        RESPONDED = 'RESPONDED', 'Provider Responded'
        DECLINED = 'DECLINED', 'Provider Declined'
        NO_RESPONSE = 'NO_RESPONSE', 'No Response'
        EXPIRED = 'EXPIRED', 'Expired'

    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='provider_quote_requests'
    )
    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='quote_requests'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quote Request for {self.request.request_number} -> {self.provider.company_name} [{self.get_status_display()}]"


class ProviderQuote(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_NEGOTIATION = 'UNDER_NEGOTIATION', 'Under Negotiation'
        ACCEPTED_BY_BROKER = 'ACCEPTED_BY_BROKER', 'Accepted by Broker'
        DECLINED_BY_BROKER = 'DECLINED_BY_BROKER', 'Declined by Broker'
        SUPERSEDED = 'SUPERSEDED', 'Superseded by Revised Quote'

    quote_request = models.ForeignKey(
        ProviderQuoteRequest,
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    offered_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Wholesale cost offered by provider (Commercial secret)."
    )
    proposed_vehicle = models.ForeignKey(
        'fleet.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposed_quotes'
    )
    notes = models.TextField(blank=True, null=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.SUBMITTED
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quote {self.id} from {self.provider.company_name}: GHS {self.offered_cost:,}"


class QuoteNegotiation(models.Model):
    provider_quote = models.ForeignKey(
        ProviderQuote,
        on_delete=models.CASCADE,
        related_name='negotiations'
    )
    broker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quote_negotiations'
    )
    proposed_counter_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    notes = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Negotiation on Quote {self.provider_quote.id} by {self.broker.username}"


class CustomerQuote(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent to Customer'
        ACCEPTED = 'ACCEPTED', 'Accepted by Customer'
        DECLINED = 'DECLINED', 'Declined by Customer'
        CHANGE_REQUESTED = 'CHANGE_REQUESTED', 'Customer Requested Change'

    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='customer_quotes'
    )
    selected_provider_quote = models.ForeignKey(
        ProviderQuote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_quotations'
    )
    # Protected commercial fields (US-49, US-108)
    provider_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Protected: Provider cost hidden from corporate customer."
    )
    margin_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Protected: FlexyRide commission/margin hidden from corporate customer."
    )
    final_customer_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final price visible to and charged to corporate customer."
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    customer_decision_at = models.DateTimeField(null=True, blank=True)
    customer_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Customer notes, change request details, or decline reason."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_customer_quotes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_margin(self):
        """Helper to calculate margin amount."""
        if self.final_customer_price and self.provider_cost:
            return self.final_customer_price - self.provider_cost
        return 0.00

    def save(self, *args, **kwargs):
        if self.final_customer_price and self.provider_cost:
            self.margin_amount = self.final_customer_price - self.provider_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Customer Quote for {self.request.request_number}: GHS {self.final_customer_price:,} [{self.get_status_display()}]"


class CommissionTier(models.Model):
    """
    Automated commission percentage tiers configurable by system admin.
    Calculates the FlexyRide commercial markup on top of provider wholesale costs.
    """
    name = models.CharField(
        max_length=100,
        help_text="Descriptive tier name (e.g. Standard SUV 25%, VIP Luxury 30%)"
    )
    vehicle_category = models.CharField(
        max_length=30,
        choices=[
            ('SEDAN', 'Standard Sedan'),
            ('EXECUTIVE', 'Executive Saloon'),
            ('SUV', 'SUV / 4x4'),
            ('VAN', 'Passenger Van'),
            ('MINIBUS', 'Minibus / Shuttle'),
            ('COASTER_BUS', 'Coaster Bus'),
            ('LUXURY', 'VIP / Luxury Vehicle'),
        ],
        blank=True,
        null=True,
        help_text="Leave blank to match all vehicle categories"
    )
    min_distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Minimum distance for tier in km"
    )
    max_distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank for open-ended maximum distance"
    )
    margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        help_text="FlexyRide commission percentage to apply (e.g. 25.00 for 25%)"
    )
    min_margin_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
        help_text="Minimum guaranteed FlexyRide commission in GHS"
    )
    auto_dispatch_quote = models.BooleanField(
        default=True,
        help_text="If enabled, accepting an RFQ instantly generates and dispatches the customer quote without manual broker delay."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this commission tier is actively evaluated"
    )
    priority = models.PositiveIntegerField(
        default=10,
        help_text="Evaluation priority: higher priority rules match first"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']
        verbose_name = 'Commission Percentage Tier'
        verbose_name_plural = 'Commission Percentage Tiers'

    def __str__(self):
        cat = self.get_vehicle_category_display() if self.vehicle_category else "All Vehicles"
        return f"{self.name} ({cat}: {self.margin_percentage}%)"

    @classmethod
    def get_tier_for_request(cls, request_obj):
        """
        Finds the most specific active commission tier for the given request.
        Matches by vehicle category and distance range.
        Falls back to a general tier or a default 20% tier.
        """
        from decimal import Decimal
        category = getattr(request_obj, 'requested_vehicle_category', None)
        distance = Decimal(str(getattr(request_obj, 'estimated_distance_km', 0) or 0))

        active_tiers = cls.objects.filter(is_active=True).order_by('-priority', '-min_distance_km')

        # 1. First attempt: Match specific vehicle category + distance
        if category:
            for tier in active_tiers.filter(vehicle_category=category):
                if distance >= tier.min_distance_km:
                    if tier.max_distance_km is None or distance <= tier.max_distance_km:
                        return tier

        # 2. Second attempt: Match global tier (null or empty category) + distance
        for tier in active_tiers.filter(models.Q(vehicle_category__isnull=True) | models.Q(vehicle_category='')):
            if distance >= tier.min_distance_km:
                if tier.max_distance_km is None or distance <= tier.max_distance_km:
                    return tier

        # 3. Fallback: Any active tier or dummy 20%
        first = active_tiers.first()
        if first:
            return first

        # Synthetic fallback
        return cls(
            name="Default Base Margin",
            margin_percentage=Decimal('20.00'),
            min_margin_amount=Decimal('50.00'),
            auto_dispatch_quote=True
        )

