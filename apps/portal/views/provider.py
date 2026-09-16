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
