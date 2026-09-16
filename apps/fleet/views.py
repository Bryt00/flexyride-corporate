"""Fleet and driver management views for FlexyRide Corporate."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q

from accounts.models import ProviderCompany
from fleet.models import Vehicle, Driver
from portal.selectors import get_broker_context, get_provider_context
from portal.services import handle_broker_post, handle_provider_post
from portal.views.base import is_broker, is_provider


def fleet_categories_view(request):
    """Dedicated Detailed Fleet Categories & Specifications Page."""
    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'fleet',
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'fleet/fleet_categories.html', context)


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
@user_passes_test(is_provider)
def provider_fleet_view(request):
    """Vehicle Fleet Inventory Page for Transport Suppliers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_fleet'
    return render(request, 'fleet/provider_fleet.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_drivers_view(request):
    """Driver Roster Page for Transport Suppliers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_drivers'
    return render(request, 'fleet/provider_drivers.html', ctx)
