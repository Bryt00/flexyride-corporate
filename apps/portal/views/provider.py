"""Provider Operations Workspace views for transport suppliers."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

from portal.selectors import get_provider_context
from portal.services import handle_provider_post
from portal.views.base import is_provider


@login_required
@user_passes_test(is_provider)
def provider_overview_view(request):
    """1. Operations Overview Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_overview'
    return render(request, 'portal/provider/overview.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_dispatches_view(request):
    """2. Active Dispatches Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_dispatches'
    return render(request, 'bookings/provider_dispatches.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_rfqs_view(request):
    """3. RFQs & Bids Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_rfqs'
    return render(request, 'quotations/provider_rfqs.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_fleet_view(request):
    """4. Vehicle Fleet Inventory Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_fleet'
    return render(request, 'fleet/provider_fleet.html', ctx)


from django.shortcuts import get_object_or_404

@login_required
@user_passes_test(is_provider)
def provider_vehicle_detail_view(request, vehicle_id):
    """4b. Dedicated Vehicle Profile Page."""
    from fleet.models import Vehicle
    from portal.selectors import get_provider_context
    ctx = get_provider_context(request)
    
    # Ensure the vehicle belongs to the provider's fleet
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('provider_company').prefetch_related('photos'), 
        id=vehicle_id, 
        provider_company=ctx['company']
    )
    
    # We can fetch upcoming dispatches for this specific vehicle here
    # from bookings.models import VehicleAssignment
    # upcoming_assignments = VehicleAssignment.objects.filter(vehicle=vehicle, status__in=['ASSIGNED', 'IN_PROGRESS']).select_related('request')
    # ctx['upcoming_assignments'] = upcoming_assignments
    
    ctx['active_tab'] = 'provider_fleet'
    ctx['vehicle'] = vehicle
    return render(request, 'fleet/provider_vehicle_detail.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_drivers_view(request):
    """5. Driver Roster Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_drivers'
    return render(request, 'fleet/provider_drivers.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_compliance_view(request):
    """6. Compliance Vault Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_compliance'
    return render(request, 'compliance/provider_compliance.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_payouts_view(request):
    """7. Earnings & Payouts Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_payouts'
    return render(request, 'payments/provider_payouts.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_company_view(request):
    """8. Company Profile Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_company'
    return render(request, 'fleet/provider_company.html', ctx)


# Dedicated Profile alias & Backward compatibility alias
provider_profile_view = provider_company_view
provider_workspace_view = provider_overview_view
