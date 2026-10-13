"""Public landing pages, PWA endpoints and open tracking views for FlexyRide Corporate."""
import os
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control

from accounts.models import CorporateCustomer
from bookings.models import TransportationRequest
from fleet.models import Vehicle, Driver


def landing_page_view(request):
    """Screen 0: High-Converting Enterprise B2B Landing Page for FlexyRide Corporate."""
    cache_key = 'flexyride_landing_stats'
    stats = cache.get(cache_key)
    if stats is None:
        total_clients = CorporateCustomer.objects.count()
        total_vehicles = Vehicle.objects.count()
        total_drivers = Driver.objects.count()
        completed_trips = TransportationRequest.objects.filter(
            booking_status=TransportationRequest.BookingStatus.COMPLETED
        ).count()
        stats = {
            'total_clients': total_clients,
            'total_vehicles': total_vehicles,
            'total_drivers': total_drivers,
            'completed_trips': f"{completed_trips:,}",
            'sla_on_time': '99.4%',
            'coverage_cities': 'Accra, Tema, Kumasi, Takoradi, Tamale',
        }
        cache.set(cache_key, stats, 300)  # Cache for 5 minutes

    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'home',
        'stats': stats,
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'portal/landing.html', context)


@cache_control(public=True, max_age=600)
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


@cache_control(public=True, max_age=600)
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


@cache_control(public=True, max_age=600)
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


@cache_control(public=True, max_age=600)
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


@cache_control(public=True, max_age=86400)
def manifest_view(request):
    """Serve PWA Web App Manifest with correct MIME type and caching headers."""
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'portal', 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        content = '{}'
    return HttpResponse(content, content_type='application/manifest+json; charset=utf-8')


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def service_worker_view(request):
    """Serve Service Worker from domain root with root scope allowance."""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'portal', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        content = ''
    response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    return response


def offline_view(request):
    """Branded offline fallback page for PWA when network is unavailable."""
    return render(request, 'portal/offline.html', {
        'hide_sidebar': True,
        'hide_navbar': True,
    })

