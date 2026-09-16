"""Compliance and safety standards views for FlexyRide Corporate."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

from portal.selectors import get_provider_context
from portal.services import handle_provider_post
from portal.views.base import is_provider


def compliance_safety_view(request):
    """Dedicated Detailed Compliance & Safety Standards Page."""
    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'compliance',
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'compliance/compliance_safety.html', context)


@login_required
@user_passes_test(is_provider)
def provider_compliance_view(request):
    """Compliance Vault Page for Transport Suppliers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_compliance'
    return render(request, 'compliance/provider_compliance.html', ctx)
