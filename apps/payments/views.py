"""Payments, billing statements, and financial gateway views."""
import json
import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from bookings.models import TransportationRequest
from payments.models import PaymentTransaction, PaymentReceipt, Invoice
from payments import paystack
from feedback.models import BookingTimeline
from notifications.models import Notification
from notifications.webpush import dispatch_notification
from portal.selectors import _get_customer_company, get_broker_context, get_provider_context
from portal.services import handle_broker_post, handle_provider_post
from portal.views.base import is_corporate, is_broker, is_provider


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
def receipt_printable_view(request, receipt_ref):
    """Print-ready official VAT tax receipt view (US-23, US-106)."""
    payment = get_object_or_404(
        PaymentTransaction.objects.select_related('request', 'request__customer'),
        transaction_reference=receipt_ref
    )
    req = payment.request
    return render(request, 'payments/receipt_printable.html', {
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
    return render(request, 'payments/invoice_printable.html', {
        'invoice': invoice,
        'customer': invoice.customer,
        'line_items': invoice.line_items.all()
    })


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
        event = json.loads(payload.decode('utf-8'))
    except Exception:
        return HttpResponse("Malformed JSON", status=400)

    event_type = event.get('event')
    data = event.get('data', {})

    if event_type == 'charge.success':
        ref = data.get('reference')
        payment = PaymentTransaction.objects.filter(transaction_reference=ref).first()
        if payment:
            payment.status = PaymentTransaction.Status.SUCCESSFUL
            payment.gateway_reference = data.get('id', ref)
            payment.payment_date = timezone.now()
            payment.save()

            req = payment.request
            req.booking_status = TransportationRequest.BookingStatus.CONFIRMED
            req.save()

            BookingTimeline.objects.create(
                request=req,
                action_type='STATUS_CHANGE',
                previous_status='QUOTE_AVAILABLE',
                new_status='CONFIRMED',
                description=f"Payment verified via Paystack Webhook: Ref {ref}"
            )

            if req.requester:
                dispatch_notification(
                    user=req.requester,
                    request_obj=req,
                    title="Payment Received",
                    message=f"Payment for journey {req.request_number} confirmed via Paystack webhook.",
                    notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
                    url=f"/portal/bookings/{req.request_number}/confirmed/"
                )

    return HttpResponse("Webhook received", status=200)


@login_required
@user_passes_test(is_broker)
def broker_financials_view(request):
    """Broker Commission Margins, Settlement Reconciliation & GRA E-VAT Ledger."""
    if request.method == 'POST':
        return handle_broker_post(request)
    context = get_broker_context(request)
    context['active_tab'] = 'broker_financials'
    return render(request, 'payments/broker_financials.html', context)


@login_required
@user_passes_test(is_provider)
def provider_payouts_view(request):
    """Earnings & Payouts Page for Transport Suppliers."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_payouts'
    return render(request, 'payments/provider_payouts.html', ctx)
