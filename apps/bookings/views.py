"""Transportation requests, bookings, and live dispatch views."""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from accounts.models import User, CorporateCustomer, CompanyEmployee
from bookings.models import TransportationRequest, CancellationRequest
from bookings.forms import TransportationRequestForm, PassengerInfoForm
from quotations.models import CustomerQuote
from portal.selectors import _get_customer_company, get_broker_context, get_provider_context, UPCOMING_STATUSES
from portal.services import handle_broker_post, handle_provider_post
from portal.views.base import is_corporate, is_broker, is_provider, can_view_request


@login_required
@user_passes_test(is_corporate)
def new_request_view(request):
    """Screens 3-8: 6-Step New Transport Request Wizard."""
    company = _get_customer_company(request.user)

    if request.method == 'POST':
        request_form = TransportationRequestForm(request.POST)
        passenger_form = PassengerInfoForm(request.POST)

        if not company:
            company = CorporateCustomer.objects.filter(status=CorporateCustomer.Status.APPROVED).first() or CorporateCustomer.objects.first()
            if not company:
                company = CorporateCustomer.objects.create(
                    company_name=request.user.get_full_name() or request.user.username + " Corporate",
                    contact_email=request.user.email,
                    contact_phone=getattr(request.user, 'phone_number', '+233240000000'),
                    status=CorporateCustomer.Status.APPROVED,
                    preferred_currency='GHS'
                )
                CompanyEmployee.objects.create(company=company, user=request.user, can_approve_requests=True)

        if request_form.is_valid() and passenger_form.is_valid() and company:
            transport_request = request_form.save(commit=False)
            transport_request.customer = company
            transport_request.requester = request.user
            transport_request.save()

            passenger = passenger_form.save(commit=False)
            passenger.request = transport_request
            passenger.is_primary = True
            passenger.save()

            messages.success(request, f"Transport request {transport_request.request_number} submitted successfully!")
            return redirect('portal_request_success', request_id=transport_request.request_number)
        else:
            errors_list = []
            for field, errs in request_form.errors.items():
                for e in errs:
                    errors_list.append(f"{field.replace('_', ' ').title()}: {e}")
            for field, errs in passenger_form.errors.items():
                for e in errs:
                    errors_list.append(f"Passenger {field.replace('_', ' ').title()}: {e}")
            if errors_list:
                messages.error(request, "Failed to submit request: " + " • ".join(errors_list))

            step2_fields = {'pickup_address', 'destination_address', 'departure_datetime', 'return_datetime', 'flight_datetime', 'flight_number', 'airport_name'}
            step3_fields = {'full_name', 'phone_number', 'email'}
            if any(f in request_form.errors for f in ['journey_type']):
                error_step = 1
            elif any(f in request_form.errors for f in step2_fields):
                error_step = 2
            elif any(f in passenger_form.errors for f in step3_fields) or 'passenger_count' in request_form.errors:
                error_step = 3
            elif any(f in request_form.errors for f in ['requested_vehicle_category']):
                error_step = 4
            else:
                error_step = 2
    else:
        tomorrow = timezone.now() + timezone.timedelta(days=1)
        initial_departure = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        request_form = TransportationRequestForm(initial={'departure_datetime': initial_departure})
        passenger_form = PassengerInfoForm(initial={
            'full_name': request.user.get_full_name() or request.user.username,
            'phone_number': getattr(request.user, 'phone_number', ''),
            'email': request.user.email
        })
        error_step = 1

    return render(request, 'bookings/request_wizard.html', {
        'active_tab': 'new_request',
        'request_form': request_form,
        'passenger_form': passenger_form,
        'initial_step': error_step
    })


@login_required
@user_passes_test(is_corporate)
def request_success_view(request, request_id='FRC-00000000'):
    """Screen 9: Request Success Confirmation."""
    return render(request, 'bookings/request_success.html', {
        'request_id': request_id,
        'active_tab': 'requests'
    })


@login_required
@user_passes_test(can_view_request)
def request_details_view(request, request_id='FRC-00000000'):
    """Screen 10: Request Details & Being Arranged Lifecycle — Real data from DB."""
    is_staff_or_broker = (
        request.user.role in [User.Role.BROKER, User.Role.SYSTEM_ADMIN]
        or request.user.is_superuser
        or request.user.is_staff
    )
    if is_staff_or_broker:
        req = get_object_or_404(
            TransportationRequest.objects.select_related('customer', 'requester')
                .prefetch_related('passengers', 'timeline_events', 'customer_quotes', 'vehicle_assignments__vehicle', 'vehicle_assignments__driver'),
            request_number=request_id
        )
        company = req.customer
    else:
        company = _get_customer_company(request.user)
        req = get_object_or_404(
            TransportationRequest.objects.select_related('customer', 'requester')
                .prefetch_related('passengers', 'timeline_events', 'customer_quotes', 'vehicle_assignments__vehicle', 'vehicle_assignments__driver'),
            request_number=request_id,
            customer=company
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cancel_booking':
            reason = request.POST.get('reason', 'Customer requested cancellation')
            CancellationRequest.objects.create(
                request=req,
                cancelled_by=request.user,
                reason=reason,
                status='APPROVED'
            )
            req.booking_status = TransportationRequest.BookingStatus.CANCELLED
            req.save()
            messages.success(request, f"Booking {req.request_number} has been cancelled.")
            if is_staff_or_broker:
                return redirect('portal_broker_dispatches')
            return redirect('portal_dashboard')

        elif action == 'accept_quote':
            quote_id = request.POST.get('quote_id')
            quote = CustomerQuote.objects.filter(id=quote_id, request=req).first()
            if quote:
                quote.status = CustomerQuote.Status.ACCEPTED
                quote.customer_decision_at = timezone.now()
                quote.save()
                req.booking_status = TransportationRequest.BookingStatus.CONFIRMED
                req.save()
                messages.success(request, f"Quote accepted! Proceeding to payment.")
                return redirect('portal_payment', request_id=req.request_number)

        elif action == 'decline_quote':
            quote_id = request.POST.get('quote_id')
            quote = CustomerQuote.objects.filter(id=quote_id, request=req).first()
            if quote:
                quote.status = CustomerQuote.Status.DECLINED
                quote.customer_decision_at = timezone.now()
                quote.customer_notes = request.POST.get('notes', '')
                quote.save()
                messages.info(request, f"Quote declined.")
            return redirect('portal_request_details', request_id=req.request_number)

    timeline = req.timeline_events.all().order_by('-timestamp')[:10]
    primary_passenger = req.passengers.filter(is_primary=True).first() or req.passengers.first()
    customer_quote = req.customer_quotes.exclude(status__in=['DECLINED']).order_by('-created_at').first()
    assignment = req.vehicle_assignments.exclude(status__in=['CANCELLED', 'REPLACED']).first()

    status_stage_map = {
        'REQUEST_SUBMITTED': 1,
        'AWAITING_INTERNAL_APPROVAL': 1,
        'APPROVED_BY_COMPANY': 2,
        'RECEIVED_BY_FLEXYRIDE': 2,
        'BEING_ARRANGED': 3,
        'QUOTE_AVAILABLE': 4,
        'AWAITING_CUSTOMER_ACCEPTANCE': 4,
        'CONFIRMED': 5,
        'ASSIGNED': 6,
        'DRIVER_EN_ROUTE': 7,
        'DRIVER_ARRIVED': 7,
        'PASSENGER_ONBOARD': 7,
        'TRIP_IN_PROGRESS': 7,
        'COMPLETED': 8,
        'CANCELLED': 0,
    }
    current_stage = status_stage_map.get(req.booking_status, 1)

    return render(request, 'bookings/request_details.html', {
        'req': req,
        'request_id': request_id,
        'company': company,
        'is_staff_or_broker': is_staff_or_broker,
        'active_tab': 'requests',
        'timeline': timeline,
        'primary_passenger': primary_passenger,
        'customer_quote': customer_quote,
        'assignment': assignment,
        'current_stage': current_stage,
    })


@login_required
@user_passes_test(is_corporate)
def confirmed_booking_view(request, booking_id='FRC-00000000'):
    """Screen 14: Confirmed Booking — Shows real Vehicle & Driver assignment."""
    company = _get_customer_company(request.user)
    req = get_object_or_404(
        TransportationRequest.objects.select_related('customer'),
        request_number=booking_id,
        customer=company
    )
    assignment = req.vehicle_assignments.exclude(
        status__in=['CANCELLED', 'REPLACED']
    ).select_related('vehicle', 'driver').first()

    return render(request, 'bookings/confirmed_booking.html', {
        'req': req,
        'assignment': assignment,
        'booking_id': booking_id,
        'active_tab': 'upcoming'
    })


@login_required
@user_passes_test(is_corporate)
def live_journey_view(request, booking_id='FRC-00000000'):
    """Screen 15: Live Journey Tracking — Loads real assignment data."""
    company = _get_customer_company(request.user)
    req = get_object_or_404(TransportationRequest, request_number=booking_id, customer=company)
    assignment = req.vehicle_assignments.exclude(
        status__in=['CANCELLED', 'REPLACED']
    ).select_related('vehicle', 'driver').first()

    return render(request, 'bookings/live_journey.html', {
        'req': req,
        'assignment': assignment,
        'booking_id': booking_id,
        'active_tab': 'upcoming'
    })


@login_required
@user_passes_test(is_corporate)
def upcoming_trips_view(request):
    """Upcoming Corporate Trips — Dynamic from DB."""
    company = _get_customer_company(request.user)
    upcoming_trips = TransportationRequest.objects.none()
    if company:
        upcoming_trips = TransportationRequest.objects.filter(
            customer=company,
            booking_status__in=UPCOMING_STATUSES
        ).prefetch_related(
            'vehicle_assignments__vehicle', 'vehicle_assignments__driver'
        ).order_by('departure_datetime')

    return render(request, 'bookings/upcoming_trips.html', {
        'active_tab': 'upcoming',
        'upcoming_trips': upcoming_trips,
    })


@login_required
@user_passes_test(is_corporate)
def trip_history_view(request):
    """Trip History & Receipts — Dynamic from DB."""
    company = _get_customer_company(request.user)
    completed_trips = []
    total_spent = Decimal('0')
    total_kms = Decimal('0')

    if company:
        trips_qs = TransportationRequest.objects.filter(
            customer=company,
            booking_status='COMPLETED'
        ).prefetch_related(
            'vehicle_assignments__vehicle', 'vehicle_assignments__driver',
            'payments', 'customer_quotes', 'ratings', 'passengers'
        ).order_by('-departure_datetime')

        completed_trips = list(trips_qs)
        for t in completed_trips:
            total_spent += t.billed_amount
            total_kms += (t.estimated_distance_km or Decimal('0'))

    total_count = len(completed_trips)
    avg_trip_cost = (total_spent / total_count) if total_count > 0 else Decimal('0')

    return render(request, 'bookings/trip_history.html', {
        'active_tab': 'history',
        'completed_trips': completed_trips,
        'company': company,
        'metrics': {
            'total_spent': total_spent,
            'total_count': total_count,
            'total_kms': total_kms,
            'avg_cost': avg_trip_cost,
        }
    })


def passenger_tracking_view(request, tracking_token='TRK-9842-PASS'):
    """Passenger Live Journey Tracking & Rating Portal (US-28, US-30)."""
    return render(request, 'bookings/passenger_tracking.html', {
        'tracking_token': tracking_token,
        'hide_sidebar': True,
        'hide_navbar': True
    })


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
@user_passes_test(is_provider)
def provider_dispatches_view(request):
    """Active Dispatches Page for transport providers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_dispatches'
    return render(request, 'bookings/provider_dispatches.html', ctx)
