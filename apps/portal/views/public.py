"""Public landing pages and open tracking views for FlexyRide Corporate."""
from django.shortcuts import render
from accounts.models import CorporateCustomer
from bookings.models import TransportationRequest
from fleet.models import Vehicle, Driver


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


def passenger_tracking_view(request, tracking_token='TRK-9842-PASS'):
    """Passenger Live Journey Tracking & Rating Portal (US-28, US-30)."""
    return render(request, 'bookings/passenger_tracking.html', {
        'tracking_token': tracking_token,
        'hide_sidebar': True,
        'hide_navbar': True
    })
