"""Quotation, RFQ tenders, and margin calculations views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from bookings.models import TransportationRequest
from quotations.models import CustomerQuote
from portal.selectors import _get_customer_company, get_broker_context, get_provider_context
from portal.services import handle_broker_post, handle_provider_post
from portal.views.base import is_corporate, is_broker, is_provider


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
@user_passes_test(is_broker)
def broker_rfqs_view(request):
    """Broker RFQ Sourcing & Tender Desk."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_rfqs'
    return render(request, 'quotations/broker_rfqs.html', context)


@login_required
@user_passes_test(is_broker)
def broker_quotes_view(request):
    """Broker Commercial Margin Desk & Customer Quotations."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_quotes'
    return render(request, 'quotations/broker_quotes.html', context)


@login_required
@user_passes_test(is_provider)
def provider_rfqs_view(request):
    """RFQ Tenders and Bids page for transport providers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_rfqs'
    return render(request, 'quotations/provider_rfqs.html', ctx)
