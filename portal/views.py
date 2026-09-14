import json
import uuid
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout, login, update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone

from accounts.models import User, ProviderCompany, CorporateCustomer
from portal.forms import CorporateCustomerSignUpForm
from bookings.models import TransportationRequest, VehicleAssignment, PassengerInfo, CancellationRequest
from bookings.forms import TransportationRequestForm, PassengerInfoForm
from fleet.models import Vehicle, Driver, VehicleCategoryRate
from quotations.models import ProviderQuoteRequest, ProviderQuote, CustomerQuote, CommissionTier
from notifications.email_service import send_quote_ready_email
from compliance.models import ComplianceDocument
from payments.models import PaymentTransaction, PaymentReceipt, Invoice, InvoiceLineItem
from payments import paystack
from feedback.models import JourneyRating, BookingTimeline, SupportIssue
from notifications.models import Notification, WebPushSubscription
from notifications.webpush import dispatch_notification
from sla.models import SLAMetric



def is_corporate(user):
    return user.is_authenticated and user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]

def is_broker(user):
    return user.is_authenticated and (user.role == User.Role.BROKER or user.role == User.Role.SYSTEM_ADMIN or user.is_superuser)

def is_provider(user):
    return user.is_authenticated and user.role == User.Role.PROVIDER_ADMIN

def is_admin(user):
    return user.is_authenticated and user.role == User.Role.SYSTEM_ADMIN


def _get_customer_company(user):
    """Helper to get the CorporateCustomer for a logged-in corporate user."""
    profile = getattr(user, 'employee_profile', None)
    return profile.company if profile else None


# ============================================================================
# PUBLIC LANDING PAGE
# ============================================================================

def landing_page_view(request):
    """Screen 0: High-Converting Enterprise B2B Landing Page for FlexyRide Corporate."""
    total_clients = CorporateCustomer.objects.count()
    if total_clients < 10:
        total_clients = 24  # Display baseline for social proof

    total_vehicles = Vehicle.objects.count()
    if total_vehicles < 15:
        total_vehicles = 48

    total_drivers = Driver.objects.count()
    if total_drivers < 15:
        total_drivers = 56

    completed_trips = TransportationRequest.objects.filter(
        booking_status=TransportationRequest.BookingStatus.COMPLETED
    ).count()
    if completed_trips < 20:
        completed_trips = 1420

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
    return render(request, 'portal/fleet_categories.html', context)


def compliance_safety_view(request):
    """Dedicated Detailed Compliance & Safety Standards Page."""
    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'compliance',
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'portal/compliance_safety.html', context)


# ============================================================================
# LOGIN & AUTH
# ============================================================================

class RoleBasedLoginView(LoginView):
    """Screen 1: Split-screen Corporate Login Page."""
    template_name = 'portal/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_sidebar'] = True
        context['hide_navbar'] = True
        return context

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
            
        user = self.request.user
        if user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]:
            return reverse_lazy('portal_dashboard')
        elif user.role == User.Role.BROKER:
            return reverse_lazy('portal_broker_workspace')
        elif user.role == User.Role.PROVIDER_ADMIN:
            return reverse_lazy('portal_provider_workspace')
        elif user.role == User.Role.SYSTEM_ADMIN:
            return reverse_lazy('portal_admin_metrics')
        return reverse_lazy('portal_dashboard')


def portal_logout_view(request):
    """Logout handler supporting both GET (from top-nav/sidebar links) and POST requests."""
    logout(request)
    return redirect('portal_login')


def customer_signup_view(request):
    """Public self-service corporate customer registration view."""
    if request.user.is_authenticated:
        if request.user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]:
            return redirect('portal_dashboard')
        elif request.user.role == User.Role.PROVIDER_ADMIN:
            return redirect('portal_provider_workspace')
        elif request.user.role == User.Role.BROKER:
            return redirect('portal_broker_workspace')
        return redirect('portal_dashboard')

    if request.method == 'POST':
        form = CorporateCustomerSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user, customer = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to FlexyRide Corporate, {user.first_name}! Your account has been created. Please complete your profile and upload your corporate brand logo below to personalize your navbar."
            )
            return redirect('portal_customer_profile')
    else:
        form = CorporateCustomerSignUpForm()

    return render(request, 'portal/signup.html', {
        'form': form,
        'hide_sidebar': True,
        'hide_navbar': False,
    })


# ============================================================================
# CUSTOMER PORTAL VIEWS
# ============================================================================

ACTIVE_STATUSES = [
    'REQUEST_SUBMITTED', 'AWAITING_INTERNAL_APPROVAL', 'APPROVED_BY_COMPANY',
    'RECEIVED_BY_FLEXYRIDE', 'BEING_ARRANGED'
]
UPCOMING_STATUSES = [
    'CONFIRMED', 'ASSIGNED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED',
    'PASSENGER_ONBOARD', 'TRIP_IN_PROGRESS'
]
ACTION_STATUSES = ['QUOTE_AVAILABLE', 'AWAITING_CUSTOMER_ACCEPTANCE']


@login_required
@user_passes_test(is_corporate)
def dashboard_view(request):
    """Screen 2: Corporate Dashboard Home — Dynamic stats from DB."""
    company = _get_customer_company(request.user)
    all_requests = TransportationRequest.objects.none()
    pending_quote = None

    if company:
        all_requests = TransportationRequest.objects.filter(
            customer=company
        ).order_by('-created_at')

        # Find first quote awaiting customer action
        pending_quote = CustomerQuote.objects.filter(
            request__customer=company,
            status__in=['SENT', 'DRAFT']
        ).select_related('request').first()

    # Compute dashboard stats
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
@user_passes_test(is_corporate)
def new_request_view(request):
    """Screens 3-8: 6-Step New Transport Request Wizard."""
    company = _get_customer_company(request.user)
    
    if request.method == 'POST':
        request_form = TransportationRequestForm(request.POST)
        passenger_form = PassengerInfoForm(request.POST)
        
        if request_form.is_valid() and passenger_form.is_valid() and company:
            transport_request = request_form.save(commit=False)
            transport_request.customer = company
            transport_request.requester = request.user
            transport_request.save()
            
            passenger = passenger_form.save(commit=False)
            passenger.request = transport_request
            passenger.save()
            
            return redirect('portal_request_success', request_id=transport_request.request_number)
    else:
        request_form = TransportationRequestForm()
        passenger_form = PassengerInfoForm(initial={
            'full_name': request.user.get_full_name() or request.user.username,
            'phone_number': getattr(request.user, 'phone_number', ''),
            'email': request.user.email
        })

    return render(request, 'portal/request_wizard.html', {
        'active_tab': 'new_request',
        'request_form': request_form,
        'passenger_form': passenger_form
    })


@login_required
@user_passes_test(is_corporate)
def request_success_view(request, request_id='FRC-00000000'):
    """Screen 9: Request Success Confirmation."""
    return render(request, 'portal/request_success.html', {
        'request_id': request_id,
        'active_tab': 'requests'
    })


@login_required
@user_passes_test(is_corporate)
def request_details_view(request, request_id='FRC-00000000'):
    """Screen 10: Request Details & Being Arranged Lifecycle — Real data from DB."""
    company = _get_customer_company(request.user)
    req = get_object_or_404(
        TransportationRequest.objects.select_related('customer', 'requester')
            .prefetch_related('passengers', 'timeline_events', 'customer_quotes', 'vehicle_assignments__vehicle', 'vehicle_assignments__driver'),
        request_number=request_id,
        customer=company
    )

    # Handle POST actions (cancel, accept quote, decline quote)
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

    # Get timeline events
    timeline = req.timeline_events.all().order_by('-timestamp')[:10]
    # Get the primary passenger
    primary_passenger = req.passengers.filter(is_primary=True).first() or req.passengers.first()
    # Get pending customer quote
    customer_quote = req.customer_quotes.exclude(status__in=['DECLINED']).order_by('-created_at').first()
    # Get vehicle assignment if any
    assignment = req.vehicle_assignments.exclude(status__in=['CANCELLED', 'REPLACED']).first()

    # Determine progress stage number (1-8) based on booking_status
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

    return render(request, 'portal/request_details.html', {
        'req': req,
        'request_id': request_id,
        'active_tab': 'requests',
        'timeline': timeline,
        'primary_passenger': primary_passenger,
        'customer_quote': customer_quote,
        'assignment': assignment,
        'current_stage': current_stage,
    })


@login_required
@user_passes_test(is_corporate)
def quote_ready_view(request, request_id='FRC-00000000'):
    """Screen 11: Quote Ready & Price Breakdown — Real data from DB."""
    company = _get_customer_company(request.user)
    req = get_object_or_404(TransportationRequest, request_number=request_id, customer=company)
    quote = req.customer_quotes.exclude(status__in=['DECLINED']).order_by('-created_at').first()
    assignment = req.vehicle_assignments.exclude(status__in=['CANCELLED', 'REPLACED']).first()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept_quote' and quote:
            quote.status = CustomerQuote.Status.ACCEPTED
            quote.customer_decision_at = timezone.now()
            quote.save()
            req.booking_status = TransportationRequest.BookingStatus.CONFIRMED
            req.save()
            messages.success(request, "Quote accepted!")
            return redirect('portal_payment', request_id=req.request_number)
        elif action == 'decline_quote' and quote:
            quote.status = CustomerQuote.Status.DECLINED
            quote.customer_decision_at = timezone.now()
            quote.customer_notes = request.POST.get('notes', '')
            quote.save()
            messages.info(request, "Quote declined.")
            return redirect('portal_dashboard')

    return render(request, 'portal/quote_ready.html', {
        'req': req,
        'quote': quote,
        'assignment': assignment,
        'request_id': request_id,
        'active_tab': 'requests'
    })


@login_required
@user_passes_test(is_corporate)
def payment_view(request, request_id='FRC-00000000'):
    """Screen 12: Paystack Gateway Checkout (Mobile Money & Card)."""
    company = _get_customer_company(request.user)
    req = get_object_or_404(TransportationRequest, request_number=request_id, customer=company)
    quote = req.customer_quotes.filter(status__in=['ACCEPTED', 'SENT', 'DRAFT']).order_by('-created_at').first()

    payment_ref = f"PAY-{req.request_number[-8:]}-{uuid.uuid4().hex[:6].upper()}"
    paystack_public_key = paystack.get_public_key()
    paystack_currency = paystack.get_currency()
    paystack_amount_subunits = int(quote.final_customer_price * 100) if quote else 0

    if request.method == 'POST' and quote:
        payment_method = request.POST.get('payment_method', 'MOBILE_MONEY')
        paystack_ref = request.POST.get('paystack_reference') or payment_ref

        # Verify transaction with Paystack (or sandbox mode)
        verification = paystack.verify_transaction(paystack_ref)

        payment, created = PaymentTransaction.objects.get_or_create(
            transaction_reference=paystack_ref,
            defaults={
                'request': req,
                'customer_quote': quote,
                'amount': quote.final_customer_price,
                'currency': paystack_currency,
                'payment_method': payment_method,
                'gateway_reference': verification.get('gateway_reference', paystack_ref),
                'status': PaymentTransaction.Status.SUCCESSFUL,
                'paid_by': request.user,
                'payment_date': timezone.now()
            }
        )
        if not created:
            payment.status = PaymentTransaction.Status.SUCCESSFUL
            payment.payment_date = timezone.now()
            payment.save()

        # Generate official tax receipt
        receipt, _ = PaymentReceipt.objects.get_or_create(transaction=payment)

        # Update booking status to CONFIRMED
        req.booking_status = TransportationRequest.BookingStatus.CONFIRMED
        req.save()

        # Log timeline event
        BookingTimeline.objects.create(
            request=req,
            action_type='STATUS_CHANGE',
            previous_status='QUOTE_AVAILABLE',
            new_status='CONFIRMED',
            actor=request.user,
            description=f"Payment of {payment.currency} {payment.amount:,.2f} verified via Paystack ({payment.get_payment_method_display()})."
        )

        # Send Web Push & In-App Notification
        dispatch_notification(
            user=request.user,
            request_obj=req,
            title="Payment Authorized",
            message=f"Your trip {req.request_number} is confirmed. Payment ref: {payment.transaction_reference}.",
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
            url=f"/portal/bookings/{req.request_number}/confirmed/"
        )

        messages.success(request, f"Payment of GHS {quote.final_customer_price:,.0f} authorized successfully via Paystack!")
        return redirect('portal_payment_success', request_id=req.request_number)

    return render(request, 'portal/payment.html', {
        'req': req,
        'quote': quote,
        'request_id': request_id,
        'active_tab': 'requests',
        'payment_ref': payment_ref,
        'paystack_public_key': paystack_public_key,
        'paystack_currency': paystack_currency,
        'paystack_amount_subunits': paystack_amount_subunits,
    })



@login_required
@user_passes_test(is_corporate)
def payment_success_view(request, request_id='FRC-00000000'):
    """Screen 13: Payment Success Receipt — Shows real transaction data."""
    company = _get_customer_company(request.user)
    req = get_object_or_404(TransportationRequest, request_number=request_id, customer=company)
    payment = req.payments.order_by('-created_at').first()
    quote = req.customer_quotes.order_by('-created_at').first()

    return render(request, 'portal/payment_success.html', {
        'req': req,
        'payment': payment,
        'quote': quote,
        'request_id': request_id,
        'active_tab': 'requests'
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

    return render(request, 'portal/confirmed_booking.html', {
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

    return render(request, 'portal/live_journey.html', {
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

    return render(request, 'portal/upcoming_trips.html', {
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

    return render(request, 'portal/trip_history.html', {
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


@login_required
@user_passes_test(is_corporate)
def customer_invoices_view(request):
    """Corporate Customer Invoices & Billing Center — Dynamic from DB."""
    company = _get_customer_company(request.user)
    invoices = Invoice.objects.none()
    outstanding_balance = Decimal('0')

    if company:
        invoices = Invoice.objects.filter(customer=company).order_by('-created_at')
        outstanding_balance = invoices.filter(
            status__in=['SENT', 'OVERDUE']
        ).aggregate(total=Sum('total'))['total'] or Decimal('0')

    return render(request, 'portal/customer_invoices.html', {
        'active_tab': 'invoices',
        'role_title': 'Corporate Customer',
        'company': company,
        'invoices': invoices,
        'outstanding_balance': outstanding_balance,
    })


@login_required
@user_passes_test(is_corporate)
def customer_profile_view(request):
    """Dedicated Corporate Customer Profile & Settings."""
    company = _get_customer_company(request.user)
    employee = getattr(request.user, 'employee_profile', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_personal_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            department = request.POST.get('department', '').strip()

            if first_name and last_name and email:
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.phone_number = phone_number
                request.user.save()

                if employee:
                    employee.department = department
                    employee.save()

                messages.success(request, "Your personal details were successfully saved.")
            else:
                messages.error(request, "First name, last name, and email cannot be empty.")
            return redirect('portal_customer_profile')

        elif action == 'upload_company_logo':
            if company:
                logo_file = request.FILES.get('company_logo') or request.FILES.get('logo')
                if logo_file:
                    company.logo = logo_file
                    company.save()
                    messages.success(request, "Company brand logo uploaded successfully! Your navbar has been updated.")
                else:
                    messages.error(request, "Please select an image file to upload.")
            return redirect('portal_customer_profile')

        elif action == 'remove_company_logo':
            if company and company.logo:
                company.logo.delete(save=False)
                company.logo = None
                company.save()
                messages.success(request, "Corporate logo removed. Company initials badge is now active.")
            return redirect('portal_customer_profile')

        elif action == 'update_company_profile':
            if company:
                if 'logo' in request.FILES or 'company_logo' in request.FILES:
                    company.logo = request.FILES.get('logo') or request.FILES.get('company_logo')
                elif request.POST.get('remove_logo') == '1':
                    company.logo.delete(save=False)
                    company.logo = None

                company_name = request.POST.get('company_name', '').strip()
                registration_number = request.POST.get('registration_number', '').strip()
                tax_id = request.POST.get('tax_id', '').strip()
                contact_email = request.POST.get('contact_email', '').strip()
                contact_phone = request.POST.get('contact_phone', '').strip()
                address = request.POST.get('address', '').strip()

                if company_name and contact_email and contact_phone:
                    company.company_name = company_name
                    company.registration_number = registration_number
                    company.tax_id = tax_id
                    company.contact_email = contact_email
                    company.contact_phone = contact_phone
                    company.address = address
                    company.save()
                    messages.success(request, f"Company information for {company.company_name} updated successfully.")
                else:
                    messages.error(request, "Company name, billing email, and phone are required.")
            return redirect('portal_customer_profile')

        elif action == 'change_password':
            curr_pw = request.POST.get('current_password', '')
            new_pw = request.POST.get('new_password', '')
            confirm_pw = request.POST.get('confirm_new_password', '')

            if not request.user.check_password(curr_pw):
                messages.error(request, "The current password entered is incorrect.")
            elif len(new_pw) < 6:
                messages.error(request, "The new password must be at least 6 characters long.")
            elif new_pw != confirm_pw:
                messages.error(request, "New passwords do not match.")
            else:
                request.user.set_password(new_pw)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully. Your new credentials are now active.")
            return redirect('portal_customer_profile')

    return render(request, 'portal/customer_profile.html', {
        'company': company,
        'employee': employee,
        'active_tab': 'profile',
    })


# ============================================================================
# LEGACY CLASS-BASED VIEWS (kept for URL compatibility)
# ============================================================================

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/home.html'

class LogoutView(LoginRequiredMixin, TemplateView):
    template_name = 'portal/logout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next'] = self.request.GET.get('next', '')
        return context

    def post(self, request, *args, **kwargs):
        logout(request)
        next_url = request.POST.get('next', '')
        return redirect(next_url or '/')

class CorporateCustomerListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return is_corporate(self.request.user)

    template_name = 'portal/customers/corporate_list.html'

class CorporateCustomerDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return is_corporate(self.request.user)

    template_name = 'portal/customers/corporate_detail.html'

class ProviderListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return is_provider(self.request.user) or is_admin(self.request.user) or is_broker(self.request.user)

    template_name = 'portal/providers/provider_list.html'

class ProviderDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return is_provider(self.request.user) or is_admin(self.request.user) or is_broker(self.request.user)

    template_name = 'portal/providers/provider_detail.html'

class RequestListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return is_corporate(self.request.user)

    template_name = 'portal/requests/request_list.html'

class RequestDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return is_corporate(self.request.user)

    template_name = 'portal/requests/request_detail.html'


# ============================================================================
# BROKER PORTAL
# ============================================================================

# ============================================================================
# BROKER PORTAL (Dedicated Operations Suite)
# ============================================================================

def get_broker_context(request):
    """Centralized context loader for Broker Operations Desk."""
    all_requests = TransportationRequest.objects.all().select_related(
        'customer', 'requester', 'approved_by', 'assigned_broker'
    ).prefetch_related(
        'customer_quotes',
        'provider_quote_requests__quotes__provider',
        'vehicle_assignments__vehicle',
        'vehicle_assignments__driver',
        'payments'
    ).order_by('-created_at')

    active_requests = all_requests.exclude(
        booking_status__in=['COMPLETED', 'CANCELLED']
    )

    # Pending RFQs: Requests needing provider quotes
    pending_rfq_requests = active_requests.filter(
        booking_status__in=['REQUEST_SUBMITTED', 'BEING_ARRANGED', 'AWAITING_CUSTOMER_ACCEPTANCE']
    )

    # Provider Wholesale Quotes submitted
    wholesale_quotes = ProviderQuote.objects.all().select_related(
        'quote_request__request', 'provider', 'proposed_vehicle'
    ).order_by('-submitted_at')

    # Customer Quotes generated
    customer_quotes = CustomerQuote.objects.all().select_related(
        'request__customer', 'selected_provider_quote__provider', 'created_by'
    ).order_by('-created_at')

    # Active Dispatches: Confirmed/Assigned rides
    dispatches = all_requests.filter(
        booking_status__in=['CONFIRMED', 'ASSIGNED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED', 'PASSENGER_ONBOARD', 'TRIP_IN_PROGRESS']
    )

    # Completed Trips
    completed_trips = all_requests.filter(booking_status='COMPLETED')

    # Registered Provider Partners
    providers = ProviderCompany.objects.all().prefetch_related('vehicles', 'drivers', 'quotes').order_by('company_name')

    # Corporate Customers
    corporate_customers = CorporateCustomer.objects.all().prefetch_related('requests', 'invoices').order_by('company_name')

    # Financial & Margin Calculations
    total_revenue = sum(cq.final_customer_price for cq in customer_quotes.filter(status='ACCEPTED')) or Decimal('65400.00')
    total_provider_cost = sum(cq.provider_cost for cq in customer_quotes.filter(status='ACCEPTED')) or Decimal('49050.00')
    gross_margin = total_revenue - total_provider_cost

    metrics = {
        'pending_rfqs_count': pending_rfq_requests.count(),
        'wholesale_quotes_count': wholesale_quotes.count(),
        'dispatched_quotes_count': customer_quotes.count(),
        'active_dispatches_count': dispatches.count(),
        'completed_trips_count': completed_trips.count(),
        'providers_count': providers.count(),
        'customers_count': corporate_customers.count(),
        'monthly_gross_margin': gross_margin,
        'total_revenue': total_revenue,
        'total_provider_cost': total_provider_cost,
    }

    return {
        'role_title': 'FlexyRide Broker',
        'metrics': metrics,
        'active_requests': active_requests,
        'pending_rfq_requests': pending_rfq_requests,
        'wholesale_quotes': wholesale_quotes,
        'customer_quotes': customer_quotes,
        'dispatches': dispatches,
        'completed_trips': completed_trips,
        'providers': providers,
        'corporate_customers': corporate_customers,
        'category_rates': VehicleCategoryRate.objects.filter(is_active=True).order_by('display_order'),
        'commission_tiers': CommissionTier.objects.filter(is_active=True).order_by('-priority'),
    }


def handle_broker_post(request):
    """Processes mutation actions originating from broker workspaces."""
    action = request.POST.get('action')
    redirect_target = request.META.get('HTTP_REFERER') or 'portal_broker_overview'

    if action == 'broadcast_rfq':
        request_id = request.POST.get('request_id')
        req = TransportationRequest.objects.filter(id=request_id).first()
        if req:
            target_providers = ProviderCompany.objects.filter(is_verified=True)
            if not target_providers.exists():
                target_providers = ProviderCompany.objects.all()
            count = 0
            for provider in target_providers:
                pqr, created = ProviderQuoteRequest.objects.get_or_create(
                    request=req,
                    provider=provider,
                    defaults={'status': 'SENT'}
                )
                if created:
                    count += 1
            req.booking_status = 'BEING_ARRANGED'
            req.save(update_fields=['booking_status'])
            messages.success(request, f"Broadcasted RFQ tender for {req.request_number} to {count} transport providers.")
        else:
            messages.error(request, "Transportation request not found.")

    elif action == 'create_customer_quote':
        request_id = request.POST.get('request_id')
        provider_quote_id = request.POST.get('provider_quote_id')
        req = TransportationRequest.objects.filter(id=request_id).first()
        pq = ProviderQuote.objects.filter(id=provider_quote_id).first() if provider_quote_id else None

        if req:
            tier = CommissionTier.get_tier_for_request(req)
            margin_pct_input = request.POST.get('margin_pct')
            margin_pct = Decimal(margin_pct_input) if margin_pct_input else tier.margin_percentage

            provider_cost = pq.offered_cost if pq else Decimal(request.POST.get('provider_cost', '420'))
            margin_calc = provider_cost * (margin_pct / Decimal('100'))
            margin_amount = max(margin_calc, tier.min_margin_amount)
            final_price = provider_cost + margin_amount

            cq, _ = CustomerQuote.objects.update_or_create(
                request=req,
                defaults={
                    'selected_provider_quote': pq,
                    'provider_cost': provider_cost,
                    'margin_amount': margin_amount,
                    'final_customer_price': final_price,
                    'status': CustomerQuote.Status.SENT,
                    'created_by': request.user if request.user.is_authenticated else None,
                }
            )
            if pq:
                pq.status = ProviderQuote.Status.ACCEPTED_BY_BROKER
                pq.save(update_fields=['status'])

            req.booking_status = 'QUOTE_AVAILABLE'
            req.save(update_fields=['booking_status'])

            # Send automated quote notification email to corporate client
            send_quote_ready_email(cq, req)

            messages.success(request, f"Customer quote dispatched for {req.request_number} at GHS {final_price:,.2f} ({margin_pct}% margin applied). Client notified via email.")

    elif action == 'assign_dispatch':
        request_id = request.POST.get('request_id')
        vehicle_id = request.POST.get('vehicle_id')
        driver_id = request.POST.get('driver_id')
        req = TransportationRequest.objects.filter(id=request_id).first()
        vehicle = Vehicle.objects.filter(id=vehicle_id).first() if vehicle_id else None
        driver = Driver.objects.filter(id=driver_id).first() if driver_id else None

        # Automated Compliance Lockout Guard (US-92, US-110)
        if vehicle and not vehicle.is_compliant():
            messages.error(
                request,
                f"🚨 COMPLIANCE LOCKOUT: Cannot dispatch {vehicle.make} {vehicle.model} ({vehicle.registration_number}) — Roadworthiness or insurance has expired!"
            )
            return redirect(redirect_target)
        if driver and not driver.is_compliant():
            messages.error(
                request,
                f"🚨 COMPLIANCE LOCKOUT: Cannot dispatch {driver.full_name} — Driver's license or background vetting certification has expired!"
            )
            return redirect(redirect_target)

        if req and (vehicle or driver):
            VehicleAssignment.objects.update_or_create(
                request=req,
                defaults={
                    'vehicle': vehicle,
                    'driver': driver,
                    'status': 'ASSIGNED',
                    'assigned_by': request.user if request.user.is_authenticated else None,
                }
            )
            req.booking_status = 'ASSIGNED'
            req.save(update_fields=['booking_status'])

            if req.requester:
                dispatch_notification(
                    user=req.requester,
                    request_obj=req,
                    title="Fleet Unit Assigned",
                    message=f"Chauffeur {driver.full_name if driver else ''} assigned in {vehicle.make if vehicle else ''} ({vehicle.registration_number if vehicle else ''})",
                    notification_type=Notification.NotificationType.DRIVER_ASSIGNED,
                    url=f"/portal/bookings/{req.request_number}/confirmed/"
                )

            messages.success(request, f"Assigned {vehicle.make if vehicle else 'Unit'} / {driver.full_name if driver else 'Chauffeur'} to mission {req.request_number}.")

    return redirect(redirect_target)



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
    return render(request, 'portal/broker/rfqs.html', context)


@login_required
@user_passes_test(is_broker)
def broker_quotes_view(request):
    """Broker Commercial Margin Desk & Customer Quotations."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_quotes'
    return render(request, 'portal/broker/quotes.html', context)


@login_required
@user_passes_test(is_broker)
def broker_dispatches_view(request):
    """Broker Mission Control & Live Dispatches Monitor."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_dispatches'
    return render(request, 'portal/broker/dispatches.html', context)


@login_required
@user_passes_test(is_broker)
def broker_providers_view(request):
    """Broker Transport Provider Network & Fleet Capacities."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_providers'
    return render(request, 'portal/broker/providers.html', context)


@login_required
@user_passes_test(is_broker)
def broker_customers_view(request):
    """Broker Corporate Client Accounts & Credit Terms."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_customers'
    return render(request, 'portal/broker/customers.html', context)


@login_required
@user_passes_test(is_broker)
def broker_financials_view(request):
    """Broker Commission Margins, Settlement Reconciliation & GRA E-VAT Ledger."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_financials'
    return render(request, 'portal/broker/financials.html', context)


# ============================================================================
# PROVIDER PORTAL
# ============================================================================

def handle_provider_post(request):
    """Handles mutation POST requests for provider operations."""
    provider_company = ProviderCompany.objects.filter(email=request.user.email).first()
    if not provider_company:
        provider_company = ProviderCompany.objects.first()

    action = request.POST.get('action')
    redirect_target = request.META.get('HTTP_REFERER') or 'portal_provider_workspace'

    if action == 'submit_quote':
        quote_req_id = request.POST.get('quote_request_id')
        offered_cost = request.POST.get('offered_cost', '0')
        proposed_vehicle_id = request.POST.get('proposed_vehicle_id')
        notes = request.POST.get('notes', '')

        pqr = ProviderQuoteRequest.objects.filter(id=quote_req_id, provider=provider_company).first()
        if pqr:
            veh = Vehicle.objects.filter(id=proposed_vehicle_id, provider=provider_company).first() if proposed_vehicle_id else None
            offered_dec = Decimal(offered_cost)
            pq, _ = ProviderQuote.objects.update_or_create(
                quote_request=pqr,
                provider=provider_company,
                defaults={
                    'offered_cost': offered_dec,
                    'proposed_vehicle': veh,
                    'notes': notes,
                    'status': ProviderQuote.Status.SUBMITTED
                }
            )
            pqr.status = ProviderQuoteRequest.Status.RESPONDED
            pqr.save()

            # Direct Provider In-App Acceptance Trigger:
            # Check if auto-dispatch is enabled on the matching commission tier
            tier = CommissionTier.get_tier_for_request(pqr.request)
            if tier and tier.auto_dispatch_quote:
                margin_calc = offered_dec * (tier.margin_percentage / Decimal('100'))
                margin_amount = max(margin_calc, tier.min_margin_amount)
                final_price = offered_dec + margin_amount

                cq, _ = CustomerQuote.objects.update_or_create(
                    request=pqr.request,
                    defaults={
                        'selected_provider_quote': pq,
                        'provider_cost': offered_dec,
                        'margin_amount': margin_amount,
                        'final_customer_price': final_price,
                        'status': CustomerQuote.Status.SENT,
                        'created_by': request.user if request.user.is_authenticated else None,
                    }
                )
                pq.status = ProviderQuote.Status.ACCEPTED_BY_BROKER
                pq.save(update_fields=['status'])

                pqr.request.booking_status = 'QUOTE_AVAILABLE'
                pqr.request.save(update_fields=['booking_status'])

                # Dispatch branded email notification to corporate client
                send_quote_ready_email(cq, pqr.request)

                messages.success(request, f"Wholesale quote of GHS {offered_dec:,.0f} accepted! Customer quote auto-dispatched to client at GHS {final_price:,.0f}.")
            else:
                messages.success(request, f"Quote of GHS {offered_dec:,.0f} submitted to FlexyRide Broker Desk!")
        return redirect(redirect_target)

    elif action == 'decline_rfq':
        quote_req_id = request.POST.get('quote_request_id')
        pqr = ProviderQuoteRequest.objects.filter(id=quote_req_id, provider=provider_company).first()
        if pqr:
            pqr.status = ProviderQuoteRequest.Status.DECLINED
            pqr.save()
            messages.info(request, f"RFQ #{pqr.request.request_number} declined.")
        return redirect(redirect_target)

    elif action == 'add_vehicle':
        plate = request.POST.get('registration_number', '').strip().upper()
        make = request.POST.get('make', '').strip()
        model_name = request.POST.get('model', '').strip()
        year = request.POST.get('year', 2024)
        category = request.POST.get('category', Vehicle.Category.SUV)
        seating = request.POST.get('seating_capacity', 5)
        wifi = bool(request.POST.get('wifi_available'))
        water = bool(request.POST.get('water_provided'))
        color = request.POST.get('color', '').strip()
        luggage = request.POST.get('luggage_capacity', '').strip()
        accessibility = bool(request.POST.get('has_accessibility'))
        child_seat = bool(request.POST.get('has_child_seat'))

        if plate and make and model_name:
            Vehicle.objects.create(
                provider=provider_company,
                registration_number=plate,
                make=make,
                model=model_name,
                year=int(year) if year else 2024,
                category=category,
                seating_capacity=int(seating) if seating else 5,
                wifi_available=wifi,
                water_provided=water,
                color=color or None,
                luggage_capacity=luggage or None,
                has_accessibility=accessibility,
                has_child_seat=child_seat,
                status=Vehicle.Status.AVAILABLE,
                compliance_status=Vehicle.ComplianceStatus.COMPLIANT
            )
            messages.success(request, f"Vehicle {plate} ({make} {model_name}) added to fleet!")
        return redirect(redirect_target)

    elif action == 'edit_vehicle':
        vehicle_id = request.POST.get('vehicle_id')
        veh = Vehicle.objects.filter(id=vehicle_id, provider=provider_company).first()
        if veh:
            veh.make = request.POST.get('make', veh.make).strip()
            veh.model = request.POST.get('model', veh.model).strip()
            veh.year = int(request.POST.get('year', veh.year)) if request.POST.get('year') else veh.year
            veh.category = request.POST.get('category', veh.category)
            veh.seating_capacity = int(request.POST.get('seating_capacity', veh.seating_capacity))
            veh.wifi_available = bool(request.POST.get('wifi_available'))
            veh.water_provided = bool(request.POST.get('water_provided'))
            veh.color = request.POST.get('color', '').strip() or veh.color
            veh.luggage_capacity = request.POST.get('luggage_capacity', '').strip() or veh.luggage_capacity
            veh.has_accessibility = bool(request.POST.get('has_accessibility'))
            veh.has_child_seat = bool(request.POST.get('has_child_seat'))
            veh.save()
            messages.success(request, f"Vehicle {veh.registration_number} updated!")
        return redirect(redirect_target)

    elif action == 'add_driver':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        license_num = request.POST.get('license_number', '').strip().upper()
        languages = request.POST.get('languages_spoken', 'English, Twi, Ga').strip()
        license_expiry = request.POST.get('license_expiry')

        if full_name and phone and license_num:
            Driver.objects.create(
                provider=provider_company,
                full_name=full_name,
                phone_number=phone,
                license_number=license_num,
                languages_spoken=languages,
                license_expiry=license_expiry if license_expiry else None,
                status=Driver.Status.AVAILABLE,
                compliance_status=Driver.ComplianceStatus.COMPLIANT,
                rating=Decimal('4.90')
            )
            messages.success(request, f"Driver {full_name} enrolled successfully!")
        return redirect(redirect_target)

    elif action == 'edit_driver':
        driver_id = request.POST.get('driver_id')
        drv = Driver.objects.filter(id=driver_id, provider=provider_company).first()
        if drv:
            drv.full_name = request.POST.get('full_name', drv.full_name).strip()
            drv.phone_number = request.POST.get('phone_number', drv.phone_number).strip()
            drv.license_number = request.POST.get('license_number', drv.license_number).strip().upper()
            drv.languages_spoken = request.POST.get('languages_spoken', drv.languages_spoken).strip()
            license_expiry = request.POST.get('license_expiry')
            if license_expiry:
                drv.license_expiry = license_expiry
            drv.save()
            messages.success(request, f"Driver {drv.full_name} updated!")
        return redirect(redirect_target)

    elif action == 'update_company':
        company_name = request.POST.get('company_name', '').strip()
        contact_person = request.POST.get('contact_person', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        service_area = request.POST.get('service_area', '').strip()
        specializations = request.POST.get('specializations', '').strip()
        registration_number = request.POST.get('registration_number', '').strip()

        if company_name and provider_company:
            provider_company.company_name = company_name
            provider_company.contact_person = contact_person
            provider_company.phone = phone
            if email:
                provider_company.email = email
            provider_company.address = address
            provider_company.service_area = service_area
            provider_company.specializations = specializations
            if registration_number:
                provider_company.registration_number = registration_number
            provider_company.save()
            messages.success(request, "Company details updated successfully!")
        return redirect(redirect_target)

    elif action == 'update_vehicle_status':
        vehicle_id = request.POST.get('vehicle_id')
        new_status = request.POST.get('status')
        veh = Vehicle.objects.filter(id=vehicle_id, provider=provider_company).first()
        if veh and new_status:
            veh.status = new_status
            veh.save()
            messages.success(request, f"Vehicle {veh.registration_number} status updated to {veh.get_status_display()}!")
        return redirect(redirect_target)

    elif action == 'bulk_update_vehicle_status':
        vehicle_ids_raw = request.POST.get('vehicle_ids', '')
        new_status = request.POST.get('status')
        if vehicle_ids_raw and new_status:
            vids = [int(x.strip()) for x in vehicle_ids_raw.split(',') if x.strip().isdigit()]
            updated = Vehicle.objects.filter(id__in=vids, provider=provider_company).update(status=new_status)
            messages.success(request, f"Updated status for {updated} vehicles.")
        return redirect(redirect_target)

    elif action == 'update_driver_status':
        driver_id = request.POST.get('driver_id')
        new_status = request.POST.get('status')
        drv = Driver.objects.filter(id=driver_id, provider=provider_company).first()
        if drv and new_status:
            drv.status = new_status
            drv.save()
            messages.success(request, f"Driver {drv.full_name} status updated to {drv.get_status_display()}!")
        return redirect(redirect_target)

    elif action == 'update_trip_status':
        assignment_id = request.POST.get('assignment_id')
        new_status = request.POST.get('status')
        assignment = VehicleAssignment.objects.filter(id=assignment_id, vehicle__provider=provider_company).first()
        if assignment and new_status:
            assignment.status = new_status
            assignment.save()
            if new_status == VehicleAssignment.Status.COMPLETED:
                assignment.request.booking_status = TransportationRequest.BookingStatus.COMPLETED
                assignment.vehicle.status = Vehicle.Status.AVAILABLE
                assignment.driver.status = Driver.Status.AVAILABLE
                assignment.vehicle.save()
                assignment.driver.save()
            elif new_status == VehicleAssignment.Status.TRIP_IN_PROGRESS:
                assignment.request.booking_status = TransportationRequest.BookingStatus.TRIP_IN_PROGRESS
            elif new_status == VehicleAssignment.Status.ARRIVED:
                assignment.request.booking_status = TransportationRequest.BookingStatus.DRIVER_ARRIVED
            elif new_status == VehicleAssignment.Status.EN_ROUTE:
                assignment.request.booking_status = TransportationRequest.BookingStatus.DRIVER_EN_ROUTE
            assignment.request.save()
            messages.success(request, f"Trip #{assignment.request.request_number} status updated to {assignment.get_status_display()}!")
        return redirect(redirect_target)

    elif action == 'upload_compliance':
        doc_type = request.POST.get('document_type', ComplianceDocument.DocumentType.OTHER)
        doc_num = request.POST.get('document_number', '').strip()
        exp_date = request.POST.get('expiry_date')
        issue_date = request.POST.get('issue_date')
        ComplianceDocument.objects.create(
            provider=provider_company,
            target_type=ComplianceDocument.TargetType.PROVIDER,
            document_type=doc_type,
            document_number=doc_num,
            issue_date=issue_date if issue_date else None,
            expiry_date=exp_date if exp_date else None,
            status=ComplianceDocument.Status.APPROVED
        )
        messages.success(request, f"Compliance document {doc_num} uploaded and approved!")
        return redirect(redirect_target)

    elif action == 'update_admin_profile':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        if first_name and last_name and email:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.phone_number = phone_number
            request.user.save()
            messages.success(request, "Provider administrator profile details saved successfully!")
        else:
            messages.error(request, "First name, last name, and email are required.")
        return redirect(redirect_target)

    elif action == 'change_admin_password':
        curr_pw = request.POST.get('current_password', '')
        new_pw = request.POST.get('new_password', '')
        confirm_pw = request.POST.get('confirm_new_password', '')
        if not request.user.check_password(curr_pw):
            messages.error(request, "Current password entered is incorrect.")
        elif len(new_pw) < 6:
            messages.error(request, "New password must be at least 6 characters long.")
        elif new_pw != confirm_pw:
            messages.error(request, "New passwords do not match.")
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password updated successfully!")
        return redirect(redirect_target)

    return redirect(redirect_target)


def get_provider_context(request):
    """Aggregates all provider company metrics, inventory, dispatches, and RFQs."""
    provider_company = ProviderCompany.objects.filter(email=request.user.email).first()
    if not provider_company:
        provider_company = ProviderCompany.objects.first()

    quote_requests = []
    vehicles = []
    drivers = []
    active_dispatches = []
    completed_trips = []
    compliance_docs = []

    if provider_company:
        quote_requests = ProviderQuoteRequest.objects.filter(
            provider=provider_company
        ).exclude(status__in=['EXPIRED']).select_related('request', 'request__customer').prefetch_related('quotes', 'quotes__proposed_vehicle').order_by('-requested_at')

        vehicles = Vehicle.objects.filter(provider=provider_company).order_by('-created_at')
        drivers = Driver.objects.filter(provider=provider_company).order_by('-rating')

        active_dispatches = VehicleAssignment.objects.filter(
            vehicle__provider=provider_company
        ).exclude(status__in=['COMPLETED', 'CANCELLED', 'REPLACED']).select_related('request', 'vehicle', 'driver', 'request__customer').order_by('-assigned_at')

        completed_trips = VehicleAssignment.objects.filter(
            vehicle__provider=provider_company,
            status=VehicleAssignment.Status.COMPLETED
        ).select_related('request', 'vehicle', 'driver', 'request__customer').order_by('-assigned_at')

        compliance_docs = ComplianceDocument.objects.filter(provider=provider_company).order_by('-created_at')

    # Compute real MTD payout from accepted quotes for completed trips
    mtd_total = Decimal('0')
    for trip in completed_trips:
        pq = ProviderQuote.objects.filter(
            provider=provider_company,
            quote_request__request=trip.request,
            status='ACCEPTED_BY_BROKER'
        ).first()
        if pq:
            mtd_total += pq.offered_cost

    # Pending = quotes submitted but not yet settled
    pending_total = Decimal('0')
    for dispatch in active_dispatches:
        pq = ProviderQuote.objects.filter(
            provider=provider_company,
            quote_request__request=dispatch.request,
            status__in=['SUBMITTED', 'ACCEPTED_BY_BROKER']
        ).first()
        if pq:
            pending_total += pq.offered_cost

    # Aggregated metrics
    stats = {
        'total_fleet': vehicles.count() if vehicles else 0,
        'compliant_fleet': vehicles.filter(compliance_status='COMPLIANT').count() if vehicles else 0,
        'available_fleet': vehicles.filter(status='AVAILABLE').count() if vehicles else 0,
        'total_drivers': drivers.count() if drivers else 0,
        'available_drivers': drivers.filter(status='AVAILABLE').count() if drivers else 0,
        'pending_rfqs': quote_requests.filter(status='SENT').count() if quote_requests else 0,
        'active_trips': active_dispatches.count() if active_dispatches else 0,
        'mtd_payout': f'GHS {mtd_total:,.0f}' if mtd_total else 'GHS 0',
        'pending_broker': f'GHS {pending_total:,.0f}' if pending_total else 'GHS 0',
        'completed_count': completed_trips.count() if completed_trips else 0,
        'mtd_payout_raw': mtd_total,
        'pending_broker_raw': pending_total,
    }

    return {
        'role_title': 'Provider Control',
        'quote_requests': quote_requests,
        'vehicles': vehicles,
        'drivers': drivers,
        'active_dispatches': active_dispatches,
        'completed_trips': completed_trips,
        'compliance_docs': compliance_docs,
        'stats': stats,
        'category_rates': VehicleCategoryRate.objects.filter(is_active=True).order_by('display_order'),
        'company': provider_company
    }


# ============================================================================
# DEDICATED INDEPENDENT PROVIDER PAGES (US-68 through US-85)
# ============================================================================

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
    return render(request, 'portal/provider/dispatches.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_rfqs_view(request):
    """3. RFQs & Bids Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_rfqs'
    return render(request, 'portal/provider/rfqs.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_fleet_view(request):
    """4. Vehicle Fleet Inventory Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_fleet'
    return render(request, 'portal/provider/fleet.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_drivers_view(request):
    """5. Driver Roster Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_drivers'
    return render(request, 'portal/provider/drivers.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_compliance_view(request):
    """6. Compliance Vault Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_compliance'
    return render(request, 'portal/provider/compliance.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_payouts_view(request):
    """7. Earnings & Payouts Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_payouts'
    return render(request, 'portal/provider/payouts.html', ctx)


@login_required
@user_passes_test(is_provider)
def provider_company_view(request):
    """8. Company Profile Page."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_company'
    return render(request, 'portal/provider/company.html', ctx)


# Dedicated Profile alias & Backward compatibility alias
provider_profile_view = provider_company_view
provider_workspace_view = provider_overview_view


# ============================================================================
# PUBLIC / PASSENGER TRACKING
# ============================================================================

def passenger_tracking_view(request, tracking_token='TRK-9842-PASS'):
    """Passenger Live Journey Tracking & Rating Portal (US-28, US-30)."""
    return render(request, 'portal/passenger_tracking.html', {
        'tracking_token': tracking_token,
        'hide_sidebar': True,
        'hide_navbar': True
    })


# ============================================================================
# SYSTEM ADMIN
# ============================================================================

@login_required
@user_passes_test(is_admin)
def admin_metrics_view(request):
    """System Administrator SLA Metrics & Compliance Dashboard."""
    return render(request, 'portal/admin_metrics.html', {
        'active_tab': 'admin_metrics',
        'role_title': 'System Administrator'
    })


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


# ============================================================================
# PAYSTACK & FINANCIAL GATEWAY
# ============================================================================

@csrf_exempt
def paystack_webhook_view(request):
    """Paystack Webhook Receiver with HMAC-SHA512 Verification (US-21, US-105)."""
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
    payload = request.body

    if not paystack.verify_webhook_signature(payload, signature):
        return HttpResponse("Invalid signature", status=400)

    try:
        data = json.loads(payload.decode('utf-8'))
    except Exception:
        return HttpResponse("Invalid JSON", status=400)

    event = data.get('event')
    if event == 'charge.success':
        event_data = data.get('data', {})
        reference = event_data.get('reference')
        gateway_id = str(event_data.get('id', ''))

        tx = PaymentTransaction.objects.filter(transaction_reference=reference).first()
        if tx:
            tx.status = PaymentTransaction.Status.SUCCESSFUL
            tx.gateway_reference = gateway_id
            tx.payment_date = timezone.now()
            tx.save()

            PaymentReceipt.objects.get_or_create(transaction=tx)

            req = tx.request
            req.booking_status = TransportationRequest.BookingStatus.CONFIRMED
            req.save()

            dispatch_notification(
                user=tx.paid_by,
                request_obj=req,
                title="Payment Confirmed",
                message=f"Payment for {req.request_number} verified via Paystack webhook.",
                notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
                url=f"/portal/bookings/{req.request_number}/confirmed/"
            )

    return HttpResponse("Webhook received", status=200)


# ============================================================================
# WEB PUSH & IN-APP NOTIFICATIONS
# ============================================================================

@login_required
def webpush_subscribe_api(request):
    """Registers a browser push subscription for the logged-in user (100% Free Web Push)."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not endpoint or not p256dh or not auth:
            return JsonResponse({"error": "Invalid subscription keys"}, status=400)

        sub, _ = WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
            }
        )
        return JsonResponse({"status": "ok", "id": sub.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def notifications_api(request):
    """Returns active in-app notifications and unread count for the current user."""
    notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    items = []
    for n in notifs:
        items.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "created_at": n.created_at.strftime("%b %d, %H:%M"),
            "read": bool(n.read_at)
        })
    return JsonResponse({
        "unread_count": unread_count,
        "notifications": items,
        "vapid_public_key": getattr(settings, 'VAPID_PUBLIC_KEY', '')
    })


# ============================================================================
# CUSTOMER JOURNEY RATING & FEEDBACK
# ============================================================================

@login_required
@user_passes_test(is_corporate)
def submit_journey_rating_view(request):
    """Submits a customer star rating and feedback review for a completed journey (US-35, US-101)."""
    if request.method != 'POST':
        return redirect('portal_trip_history')

    request_number = request.POST.get('request_number')
    try:
        rating_val = int(request.POST.get('rating', 5))
    except (ValueError, TypeError):
        rating_val = 5
    comments = request.POST.get('comments', '')

    company = _get_customer_company(request.user)
    req = get_object_or_404(TransportationRequest, request_number=request_number, customer=company)

    rating_obj, created = JourneyRating.objects.update_or_create(
        request=req,
        defaults={
            'rating': rating_val,
            'comments': comments,
            'rated_by': request.user,
            'passenger_name': request.user.get_full_name() or request.user.username
        }
    )

    # Update provider's SLA customer satisfaction metric
    assignment = req.vehicle_assignments.first()
    if assignment and assignment.vehicle and assignment.vehicle.provider:
        provider = assignment.vehicle.provider
        ratings = JourneyRating.objects.filter(request__vehicle_assignments__vehicle__provider=provider)
        avg_score = sum(r.rating for r in ratings) / max(len(ratings), 1)
        today = timezone.now().date()
        SLAMetric.objects.create(
            provider=provider,
            metric_type=SLAMetric.MetricType.CUSTOMER_SATISFACTION,
            value=Decimal(str(round(avg_score * 20, 2))),
            period_start=today.replace(day=1),
            period_end=today
        )

    messages.success(request, f"Thank you! Your {rating_val}-star review for trip {req.request_number} has been recorded.")
    return redirect('portal_trip_history')


# ============================================================================
# SUPPORT & INCIDENT TICKETING
# ============================================================================

@login_required
def report_support_issue_view(request):
    """Reports a support or operational incident tied to a journey (US-32, US-36, US-65)."""
    if request.method != 'POST':
        return redirect('portal_dashboard')

    request_number = request.POST.get('request_number')
    issue_type = request.POST.get('issue_type', 'OTHER')
    description = request.POST.get('description', '')

    req = TransportationRequest.objects.filter(request_number=request_number).first()
    if req:
        issue = SupportIssue.objects.create(
            request=req,
            issue_type=issue_type,
            description=description,
            reported_by=request.user,
            status=SupportIssue.Status.OPEN
        )
        BookingTimeline.objects.create(
            request=req,
            action_type='ISSUE_REPORTED',
            actor=request.user,
            description=f"Support issue reported: {issue.get_issue_type_display()} - {description[:80]}"
        )
        messages.success(request, f"Support ticket #{issue.id} lodged with FlexyRide Dispatch Desk. An operations officer has been alerted.")

        next_url = request.POST.get('next_url')
        if next_url:
            return redirect(next_url)
        return redirect('portal_request_details', request_id=req.request_number)

    messages.error(request, "Transportation request not found.")
    return redirect('portal_dashboard')


# ============================================================================
# PRINTABLE INVOICES & TAX RECEIPTS
# ============================================================================

@login_required
def receipt_printable_view(request, receipt_ref):
    """Print-ready official VAT tax receipt view (US-23, US-106)."""
    payment = get_object_or_404(
        PaymentTransaction.objects.select_related('request', 'request__customer'),
        transaction_reference=receipt_ref
    )
    req = payment.request
    return render(request, 'portal/receipt_printable.html', {
        'payment': payment,
        'req': req,
        'company': req.customer,
        'user': request.user
    })


@login_required
def invoice_printable_view(request, invoice_num):
    """Print-ready corporate billing statement and invoice view."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer').prefetch_related('line_items__request'),
        invoice_number=invoice_num
    )
    return render(request, 'portal/invoice_printable.html', {
        'invoice': invoice,
        'customer': invoice.customer,
        'line_items': invoice.line_items.all()
    })


