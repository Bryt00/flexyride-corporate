"""Broker Operations Desk views for FlexyRide Corporate."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q

from accounts.models import ProviderCompany
from fleet.models import Vehicle, Driver
from portal.selectors import get_broker_context
from portal.services import handle_broker_post
from portal.views.base import is_broker


@login_required
@user_passes_test(is_broker)
def broker_overview_view(request):
    """FlexyRide Broker Control Center / Overview."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_overview'
    return render(request, 'portal/broker/overview.html', context)


@login_required
@user_passes_test(is_broker)
def broker_rfqs_view(request):
    """Broker RFQ Sourcing & Tender Desk."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_rfqs'
    return render(request, 'quotations/broker_rfqs.html', context)


@login_required
@user_passes_test(is_broker)
def broker_quotes_view(request):
    """Broker Commercial Margin Desk & Customer Quotations."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_quotes'
    return render(request, 'quotations/broker_quotes.html', context)


@login_required
@user_passes_test(is_broker)
def broker_dispatches_view(request):
    """Broker Mission Control & Live Dispatches Monitor."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_dispatches'
    return render(request, 'bookings/broker_dispatches.html', context)


@login_required
@user_passes_test(is_broker)
def broker_providers_view(request):
    """Broker Transport Provider Network & Fleet Capacities."""
    if request.method == 'POST':
        return handle_broker_post(request)

    context = get_broker_context(request)
    context['active_tab'] = 'broker_providers'

    status_filter = request.GET.get('status', 'ALL').upper()
    search_query = request.GET.get('q', '').strip()

    all_providers = (
        ProviderCompany.objects.all()
        .prefetch_related('vehicles', 'drivers', 'quotes', 'compliance_documents')
        .order_by('company_name')
    )

    context['total_providers_count'] = all_providers.count()
    context['approved_providers_count'] = all_providers.filter(status=ProviderCompany.Status.APPROVED).count()
    context['pending_providers_count'] = all_providers.filter(status=ProviderCompany.Status.PENDING).count()
    context['suspended_providers_count'] = all_providers.filter(status=ProviderCompany.Status.SUSPENDED).count()
    context['total_network_vehicles'] = Vehicle.objects.count()
    context['total_network_drivers'] = Driver.objects.count()

    filtered_providers = all_providers
    if status_filter in ['APPROVED', 'PENDING', 'SUSPENDED']:
        filtered_providers = filtered_providers.filter(status=status_filter)

    if search_query:
        filtered_providers = filtered_providers.filter(
            Q(company_name__icontains=search_query) |
            Q(registration_number__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(service_area__icontains=search_query) |
            Q(specializations__icontains=search_query)
        )

    context['providers'] = filtered_providers
    context['status_filter'] = status_filter
    context['search_query'] = search_query

    return render(request, 'fleet/broker_providers.html', context)


@login_required
@user_passes_test(is_broker)
def broker_customers_view(request):
    """Broker Corporate Client Accounts & Credit Terms."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_customers'
    return render(request, 'accounts/broker_customers.html', context)


@login_required
@user_passes_test(is_broker)
def broker_financials_view(request):
    """Broker Commission Margins, Settlement Reconciliation & GRA E-VAT Ledger."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_financials'
    return render(request, 'payments/broker_financials.html', context)
