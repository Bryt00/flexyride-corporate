"""Core portal landing and overview views for FlexyRide Corporate."""
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from accounts.models import User, CorporateCustomer
from bookings.models import TransportationRequest
from fleet.models import Vehicle, Driver
from quotations.models import CustomerQuote
from ..selectors import (
    _get_customer_company,
    get_broker_context,
    get_provider_context,
    ACTIVE_STATUSES,
    UPCOMING_STATUSES,
    ACTION_STATUSES,
)
from ..services import handle_broker_post, handle_provider_post
from .base import is_broker, is_provider


def landing_page_view(request):
    """Screen 0: High-Converting Enterprise B2B Landing Page for FlexyRide Corporate."""
    total_clients = CorporateCustomer.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_drivers = Driver.objects.count()
    completed_trips = TransportationRequest.objects.filter(
        booking_status=TransportationRequest.BookingStatus.COMPLETED
    ).count()

    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'home',
        'stats': {
            'total_clients': total_clients,
            'total_vehicles': total_vehicles,
            'total_drivers': total_drivers,
            'completed_trips': f"{completed_trips:,}",
            'sla_on_time': '99.4%',
            'coverage_cities': 'Accra, Tema, Kumasi, Takoradi, Tamale',
        },
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'portal/landing.html', context)


def solutions_view(request):
    """Dedicated Detailed Solutions Page."""
    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'solutions',
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'portal/solutions.html', context)


def how_it_works_view(request):
    """Dedicated Detailed How It Works Orchestration Page."""
    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'how_it_works',
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'portal/how_it_works.html', context)


@login_required
def dashboard_view(request):
    """Screen 2: Corporate Dashboard Home — Dynamic stats from DB."""
    if request.user.is_superuser or request.user.role == User.Role.SYSTEM_ADMIN:
        return redirect('portal_broker_workspace')
    elif request.user.role == User.Role.BROKER:
        return redirect('portal_broker_workspace')
    elif request.user.role == User.Role.PROVIDER_ADMIN:
        return redirect('portal_provider_workspace')

    company = _get_customer_company(request.user)
    all_requests = TransportationRequest.objects.none()
    pending_quote = None

    if company:
        all_requests = TransportationRequest.objects.filter(
            customer=company
        ).order_by('-created_at')

        pending_quote = CustomerQuote.objects.filter(
            request__customer=company,
            status__in=['SENT', 'DRAFT']
        ).select_related('request').first()

    stats = {
        'active': all_requests.filter(booking_status__in=ACTIVE_STATUSES).count(),
        'upcoming': all_requests.filter(booking_status__in=UPCOMING_STATUSES).count(),
        'action_needed': all_requests.filter(booking_status__in=ACTION_STATUSES).count(),
        'completed': all_requests.filter(booking_status='COMPLETED').count(),
    }

    return render(request, 'portal/dashboard.html', {
        'active_tab': 'dashboard',
        'requests': all_requests[:20],
        'company': company,
        'stats': stats,
        'pending_quote': pending_quote,
    })


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
def broker_customers_view(request):
    """Broker Corporate Client Accounts & Credit Terms."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_customers'
    return render(request, 'accounts/broker_customers.html', context)


@login_required
@user_passes_test(is_provider)
def provider_overview_view(request):
    """Operations Overview Page for transport providers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_overview'
    return render(request, 'portal/provider/overview.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_company_view(request):
    """Company Profile Page for transport suppliers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_company'
    return render(request, 'fleet/provider_company.html', ctx)


provider_profile_view = provider_company_view
provider_workspace_view = provider_overview_view


@login_required
def admin_seed_ecosystem_view(request):
    """Seed or refresh demonstration ecosystem data with Ghanaian fleets, bookings, and compliance."""
    if not (request.user.is_staff or request.user.role in ['SYSTEM_ADMIN', 'BROKER']):
        return HttpResponseForbidden("Administrative privileges required.")

    try:
        from seed_full_ecosystem import seed_full
        seed_full()
        messages.success(request, "Demonstration ecosystem initialized successfully! Ghanaian fleets, corporate bookings, quotes, and compliance records are now loaded.")
    except Exception as e:
        messages.error(request, f"Ecosystem seed error: {str(e)}")

    return redirect('admin:index')
