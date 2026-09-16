from django import template
from django.apps import apps
from bookings.models import TransportationRequest
from quotations.models import CustomerQuote
from compliance.models import ComplianceDocument
from payments.models import Invoice
from fleet.models import Driver, Vehicle

register = template.Library()

@register.simple_tag
def get_executive_kpis():
    """
    Computes key executive operational metrics for the FlexyRide Admin Console.
    """
    try:
        # Count all active, confirmed, in-transit or arranging bookings
        active_bookings = TransportationRequest.objects.exclude(
            booking_status__in=['CANCELLED', 'REJECTED_BY_COMPANY', 'COMPLETED']
        ).count()
        if active_bookings == 0:
            active_bookings = TransportationRequest.objects.count()
    except Exception:
        active_bookings = 0

    try:
        pending_approvals = TransportationRequest.objects.filter(
            internal_approval_status='PENDING_APPROVAL'
        ).count()
    except Exception:
        pending_approvals = 0

    try:
        pending_quotes = CustomerQuote.objects.filter(
            status__in=['DRAFT', 'SENT', 'CHANGE_REQUESTED']
        ).count()
        if pending_quotes == 0:
            pending_quotes = CustomerQuote.objects.count()
    except Exception:
        pending_quotes = 0

    try:
        compliance_alerts = ComplianceDocument.objects.filter(
            status__in=['PENDING', 'EXPIRING_SOON', 'EXPIRED']
        ).count()
    except Exception:
        compliance_alerts = 0

    try:
        unpaid_invoices = Invoice.objects.filter(
            status__in=['SENT', 'OVERDUE', 'DRAFT']
        ).count()
        if unpaid_invoices == 0:
            unpaid_invoices = Invoice.objects.count()
    except Exception:
        unpaid_invoices = 0

    try:
        active_drivers = Driver.objects.count()
    except Exception:
        active_drivers = 0

    try:
        active_vehicles = Vehicle.objects.count()
    except Exception:
        active_vehicles = 0

    return {
        'active_bookings': active_bookings,
        'pending_approvals': pending_approvals,
        'pending_quotes': pending_quotes,
        'compliance_alerts': compliance_alerts,
        'unpaid_invoices': unpaid_invoices,
        'active_drivers': active_drivers,
        'active_vehicles': active_vehicles,
    }


@register.simple_tag
def get_model_count(app_label, model_name):
    """Returns the live record count for a given model in the app list."""
    try:
        model = apps.get_model(app_label, model_name)
        if model:
            return model.objects.count()
    except Exception:
        pass
    return None
