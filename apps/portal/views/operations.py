"""System admin, webhook, notification, and utility operations views."""
import json
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone

from bookings.models import TransportationRequest
from payments.models import PaymentTransaction, Invoice
from payments import paystack
from feedback.models import JourneyRating, BookingTimeline, SupportIssue
from notifications.models import Notification, WebPushSubscription
from notifications.webpush import dispatch_notification
from sla.models import SLAMetric
from portal.selectors import _get_customer_company
from portal.views.base import is_admin, is_corporate


@login_required
@user_passes_test(is_admin)
def admin_metrics_view(request):
    """System Administrator SLA Metrics & Compliance Dashboard."""
    return render(request, 'sla/admin_metrics.html', {
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

    JourneyRating.objects.update_or_create(
        request=req,
        defaults={
            'rating': rating_val,
            'comments': comments,
            'rated_by': request.user,
            'passenger_name': request.user.get_full_name() or request.user.username
        }
    )

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
