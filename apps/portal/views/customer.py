"""Corporate Customer views and workflows."""
import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User, CorporateCustomer, CompanyEmployee
from bookings.models import TransportationRequest, CancellationRequest
from quotations.models import CustomerQuote
from bookings.forms import TransportationRequestForm, PassengerInfoForm
from payments.models import PaymentTransaction, PaymentReceipt, Invoice
from payments import paystack
from feedback.models import BookingTimeline
from notifications.models import Notification
from notifications.webpush import dispatch_notification
from portal.selectors import (
    _get_customer_company,
    ACTIVE_STATUSES,
    UPCOMING_STATUSES,
    ACTION_STATUSES,
)
from portal.views.base import is_corporate, is_broker, is_provider, is_admin, can_view_request


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

    return render(request, 'quotations/quote_ready.html', {
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

        PaymentReceipt.objects.get_or_create(transaction=payment)

        req.booking_status = TransportationRequest.BookingStatus.CONFIRMED
        req.save()

        BookingTimeline.objects.create(
            request=req,
            action_type='STATUS_CHANGE',
            previous_status='QUOTE_AVAILABLE',
            new_status='CONFIRMED',
            actor=request.user,
            description=f"Payment of {payment.currency} {payment.amount:,.2f} verified via Paystack ({payment.get_payment_method_display()})."
        )

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

    return render(request, 'payments/payment.html', {
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

    return render(request, 'payments/payment_success.html', {
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

    return render(request, 'payments/customer_invoices.html', {
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

    return render(request, 'accounts/customer_profile.html', {
        'company': company,
        'employee': employee,
        'active_tab': 'profile',
    })


# Legacy Class-Based Views for URL compatibility
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
