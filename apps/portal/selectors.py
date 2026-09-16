"""Query selectors and context loaders for portal application.
Encapsulates database queries, aggregations, and context assembly outside of views.
"""
from decimal import Decimal
from django.db.models import Sum, Q, Avg
from django.utils import timezone

from accounts.models import User, ProviderCompany, CorporateCustomer, CompanyEmployee
from bookings.models import TransportationRequest, VehicleAssignment
from fleet.models import Vehicle, Driver, VehicleCategoryRate
from quotations.models import ProviderQuote, CommissionTier, CustomerQuote
from compliance.models import ComplianceDocument


ACTIVE_STATUSES = [
    'REQUEST_SUBMITTED', 'AWAITING_INTERNAL_APPROVAL', 'APPROVED_BY_COMPANY',
    'RECEIVED_BY_FLEXYRIDE', 'BEING_ARRANGED'
]
UPCOMING_STATUSES = [
    'CONFIRMED', 'ASSIGNED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED',
    'PASSENGER_ONBOARD', 'TRIP_IN_PROGRESS'
]
ACTION_STATUSES = ['QUOTE_AVAILABLE', 'AWAITING_CUSTOMER_ACCEPTANCE']


def _get_customer_company(user):
    """Helper to get the CorporateCustomer for a logged-in corporate user."""
    profile = getattr(user, 'employee_profile', None)
    if profile and profile.company:
        return profile.company
    direct = CorporateCustomer.objects.filter(contact_email__iexact=user.email).first()
    if direct:
        return direct
    approved = (
        CorporateCustomer.objects.filter(status=CorporateCustomer.Status.APPROVED).first()
        or CorporateCustomer.objects.first()
    )
    if approved:
        CompanyEmployee.objects.get_or_create(
            user=user, defaults={'company': approved, 'can_approve_requests': True}
        )
        return approved
    return None


def get_broker_context(request):
    """Centralized context loader for Broker Operations Desk."""
    all_requests = (
        TransportationRequest.objects.all()
        .select_related('customer', 'requester', 'approved_by', 'assigned_broker')
        .prefetch_related(
            'customer_quotes',
            'provider_quote_requests__quotes__provider',
            'vehicle_assignments__vehicle',
            'vehicle_assignments__driver',
            'payments'
        )
        .order_by('-created_at')
    )

    active_requests = all_requests.exclude(
        booking_status__in=['COMPLETED', 'CANCELLED']
    )

    pending_rfq_requests = active_requests.filter(
        booking_status__in=['REQUEST_SUBMITTED', 'BEING_ARRANGED', 'AWAITING_CUSTOMER_ACCEPTANCE']
    )

    wholesale_quotes = (
        ProviderQuote.objects.all()
        .select_related('quote_request__request', 'provider', 'proposed_vehicle')
        .order_by('-submitted_at')
    )

    customer_quotes = (
        CustomerQuote.objects.all()
        .select_related('request__customer', 'selected_provider_quote__provider', 'created_by')
        .order_by('-created_at')
    )

    dispatches = all_requests.filter(
        booking_status__in=[
            'CONFIRMED', 'ASSIGNED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED',
            'PASSENGER_ONBOARD', 'TRIP_IN_PROGRESS'
        ]
    )

    completed_trips = all_requests.filter(booking_status='COMPLETED')
    providers = ProviderCompany.objects.all().prefetch_related('vehicles', 'drivers', 'quotes').order_by('company_name')
    corporate_customers = CorporateCustomer.objects.all().prefetch_related('requests', 'invoices').order_by('company_name')

    total_revenue = sum(cq.final_customer_price for cq in customer_quotes.filter(status='ACCEPTED')) or Decimal('0.00')
    total_provider_cost = sum(cq.provider_cost for cq in customer_quotes.filter(status='ACCEPTED')) or Decimal('0.00')
    gross_margin = total_revenue - total_provider_cost

    metrics = {
        'pending_rfqs_count': pending_rfq_requests.count(),
        'wholesale_quotes_count': wholesale_quotes.count(),
        'dispatched_quotes_count': customer_quotes.count(),
        'active_dispatches_count': dispatches.count(),
        'completed_trips_count': completed_trips.count(),
        'providers_count': providers.count(),
        'customers_count': corporate_customers.count(),
        'monthly_gross_margin': gross_margin,
        'total_revenue': total_revenue,
        'total_provider_cost': total_provider_cost,
    }

    return {
        'role_title': 'FlexyRide Corporate',
        'metrics': metrics,
        'active_requests': active_requests,
        'pending_rfq_requests': pending_rfq_requests,
        'wholesale_quotes': wholesale_quotes,
        'customer_quotes': customer_quotes,
        'dispatches': dispatches,
        'completed_trips': completed_trips,
        'providers': providers,
        'corporate_customers': corporate_customers,
        'category_rates': VehicleCategoryRate.objects.filter(is_active=True).order_by('display_order'),
        'commission_tiers': CommissionTier.objects.filter(is_active=True).order_by('-priority'),
    }


def get_provider_context(request):
    """Aggregates all provider company metrics, inventory, dispatches, and RFQs."""
    from quotations.models import ProviderQuoteRequest

    provider_company = ProviderCompany.objects.filter(email=request.user.email).first()
    if not provider_company:
        provider_company = ProviderCompany.objects.first()

    quote_requests = []
    vehicles = []
    drivers = []
    active_dispatches = []
    completed_trips = []
    compliance_docs = []

    if provider_company:
        quote_requests = (
            ProviderQuoteRequest.objects.filter(provider=provider_company)
            .exclude(status__in=['EXPIRED'])
            .select_related('request', 'request__customer')
            .prefetch_related('quotes', 'quotes__proposed_vehicle')
            .order_by('-requested_at')
        )
        vehicles = Vehicle.objects.filter(provider=provider_company).order_by('-created_at')
        drivers = Driver.objects.filter(provider=provider_company).order_by('-rating')

        active_dispatches = (
            VehicleAssignment.objects.filter(vehicle__provider=provider_company)
            .exclude(status__in=['COMPLETED', 'CANCELLED', 'REPLACED'])
            .select_related('request', 'vehicle', 'driver', 'request__customer')
            .order_by('-assigned_at')
        )

        completed_trips = (
            VehicleAssignment.objects.filter(
                vehicle__provider=provider_company,
                status=VehicleAssignment.Status.COMPLETED
            )
            .select_related('request', 'vehicle', 'driver', 'request__customer')
            .order_by('-assigned_at')
        )

        compliance_docs = ComplianceDocument.objects.filter(provider=provider_company).order_by('-created_at')

    mtd_total = Decimal('0')
    for trip in completed_trips:
        pq = ProviderQuote.objects.filter(
            provider=provider_company,
            quote_request__request=trip.request,
            status='ACCEPTED_BY_BROKER'
        ).first()
        trip.provider_quote = pq
        if pq and pq.offered_cost:
            mtd_total += pq.offered_cost

    pending_total = Decimal('0')
    for dispatch in active_dispatches:
        pq = ProviderQuote.objects.filter(
            provider=provider_company,
            quote_request__request=dispatch.request,
            status__in=['SUBMITTED', 'ACCEPTED_BY_BROKER']
        ).first()
        if pq and pq.offered_cost:
            pending_total += pq.offered_cost

    driver_avg = drivers.aggregate(avg=Avg('rating'))['avg'] if drivers else None
    if driver_avg is not None:
        avg_driver_rating = round(driver_avg, 2)
    elif provider_company and provider_company.overall_rating:
        avg_driver_rating = provider_company.overall_rating
    else:
        avg_driver_rating = Decimal('0.00')

    stats = {
        'total_fleet': vehicles.count() if vehicles else 0,
        'compliant_fleet': vehicles.filter(compliance_status='COMPLIANT').count() if vehicles else 0,
        'available_fleet': vehicles.filter(status='AVAILABLE').count() if vehicles else 0,
        'total_drivers': drivers.count() if drivers else 0,
        'available_drivers': drivers.filter(status='AVAILABLE').count() if drivers else 0,
        'pending_rfqs': quote_requests.filter(status='SENT').count() if quote_requests else 0,
        'active_trips': active_dispatches.count() if active_dispatches else 0,
        'mtd_payout': f'GHS {mtd_total:,.0f}' if mtd_total else 'GHS 0',
        'pending_broker': f'GHS {pending_total:,.0f}' if pending_total else 'GHS 0',
        'completed_count': completed_trips.count() if completed_trips else 0,
        'mtd_payout_raw': mtd_total,
        'pending_broker_raw': pending_total,
        'avg_driver_rating': avg_driver_rating,
    }

    return {
        'role_title': 'Provider Control',
        'quote_requests': quote_requests,
        'vehicles': vehicles,
        'drivers': drivers,
        'active_dispatches': active_dispatches,
        'completed_trips': completed_trips,
        'compliance_docs': compliance_docs,
        'stats': stats,
        'category_rates': VehicleCategoryRate.objects.filter(is_active=True).order_by('display_order'),
        'company': provider_company
    }
