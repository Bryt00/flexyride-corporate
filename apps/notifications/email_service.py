"""
Email Service for FlexyRide Corporate.
Dispatches branded transactional emails (Quotes, Confirmations, Receipts, Assignments)
and records notification audit history.
Supports asynchronous execution via Celery background tasks or fallback daemon threads.
"""

import sys
import logging
import threading
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from notifications.models import Notification
from notifications.webpush import dispatch_notification

logger = logging.getLogger(__name__)


def should_send_async(explicit_flag=None):
    """
    Determines if email should be sent asynchronously.
    Defaults to synchronous during tests to avoid SQLite test runner locks.
    """
    if explicit_flag is not None:
        return explicit_flag
    if 'test' in sys.argv:
        return False
    return getattr(settings, 'EMAIL_ASYNC', True)


def _thread_runner(target_func, args, kwargs):
    from django.db import connection
    connection.close()
    try:
        target_func(*args, **kwargs)
    finally:
        connection.close()


def _dispatch_async(worker_func, worker_args=(), celery_task=None, celery_args=()):
    """
    Asynchronously executes email dispatch.
    Tries Celery first; if Celery task is not available, broker is offline,
    or Celery raises any exception, it immediately executes in a background daemon thread.
    """
    dispatched = False
    if celery_task is not None:
        try:
            celery_task.delay(*celery_args)
            dispatched = True
            logger.info(f"Enqueued email to Celery task: {celery_task.name}")
        except Exception as e:
            logger.warning(f"Celery task dispatch failed or broker offline ({e}); falling back to background daemon thread.")
            dispatched = False

    if not dispatched:
        thread = threading.Thread(target=_thread_runner, args=(worker_func, worker_args, {}), daemon=True)
        thread.start()
        logger.info(f"Dispatched email to background daemon thread: {worker_func.__name__}")


# ==============================================================================
# 1. Quote Ready Email
# ==============================================================================

def send_quote_ready_email(customer_quote, request_obj, async_send=None):
    """
    Dispatches official quote ready notification email to corporate client.
    Runs asynchronously in background by default.
    """
    if should_send_async(async_send):
        try:
            from notifications.tasks import send_quote_ready_email_async
            celery_task = send_quote_ready_email_async
            celery_args = (customer_quote.id, request_obj.id)
        except Exception:
            celery_task = None
            celery_args = ()

        _dispatch_async(
            worker_func=_send_quote_ready_email_worker,
            worker_args=(customer_quote, request_obj),
            celery_task=celery_task,
            celery_args=celery_args
        )
        return True
    else:
        return _send_quote_ready_email_worker(customer_quote, request_obj)


def _send_quote_ready_email_worker(customer_quote, request_obj):
    recipient_user = getattr(request_obj, 'requester', None)
    recipient_email = None

    if recipient_user and recipient_user.email:
        recipient_email = recipient_user.email
    elif request_obj.customer and getattr(request_obj.customer, 'contact_email', None):
        recipient_email = request_obj.customer.contact_email
    elif request_obj.customer and getattr(request_obj.customer, 'billing_email', None):
        recipient_email = request_obj.customer.billing_email

    if not recipient_email:
        logger.warning(f"No recipient email found for quote ready on request {request_obj.request_number}")
        return False

    recipient_name = recipient_user.get_full_name() if recipient_user else request_obj.customer.company_name
    site_url = getattr(settings, 'SITE_URL', 'https://flexyridegh.com').rstrip('/')
    auth_url = f"{site_url}/portal/quotes/{request_obj.request_number}/"

    subject = f"Quote Ready: Transfer #{request_obj.request_number} — GHS {customer_quote.final_customer_price:,.2f}"
    context = {
        'request': request_obj,
        'quote': customer_quote,
        'recipient_name': recipient_name,
        'authorization_url': auth_url,
    }

    try:
        html_content = render_to_string('notifications/emails/quote_ready_email.html', context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'FlexyRide Corporate <noreply@flexyridegh.com>')
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        # Record email notification audit log
        Notification.objects.create(
            recipient=recipient_user,
            request=request_obj,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.QUOTE_READY,
            title=subject,
            message=f"Dispatched official binding quote of GHS {customer_quote.final_customer_price:,.2f} to {recipient_email}.",
            delivery_status=Notification.DeliveryStatus.SENT,
            sent_at=timezone.now()
        )

        logger.info(f"Quote ready email sent to {recipient_email} for #{request_obj.request_number}")

        # In-app / web push notification
        if recipient_user:
            dispatch_notification(
                user=recipient_user,
                request_obj=request_obj,
                title="Quote Ready for Authorization",
                message=f"Official quote of GHS {customer_quote.final_customer_price:,.0f} ready for #{request_obj.request_number}.",
                notification_type=Notification.NotificationType.QUOTE_READY,
                url=auth_url
            )

        return True

    except Exception as e:
        logger.error(f"Failed to send quote ready email for #{request_obj.request_number}: {e}")
        if recipient_user:
            Notification.objects.create(
                recipient=recipient_user,
                request=request_obj,
                channel=Notification.Channel.EMAIL,
                notification_type=Notification.NotificationType.QUOTE_READY,
                title=subject,
                message=f"Failed dispatching quote email to {recipient_email}: {str(e)}",
                delivery_status=Notification.DeliveryStatus.FAILED
            )
        return False


# ==============================================================================
# 2. Booking Confirmation Email
# ==============================================================================

def send_booking_confirmation_email(request_obj, quote_obj=None, payment_obj=None, async_send=None):
    """
    Dispatches booking confirmation email to corporate client.
    Runs asynchronously in background by default.
    """
    if should_send_async(async_send):
        try:
            from notifications.tasks import send_booking_confirmation_email_async
            celery_task = send_booking_confirmation_email_async
            celery_args = (request_obj.id, quote_obj.id if quote_obj else None, payment_obj.id if payment_obj else None)
        except Exception:
            celery_task = None
            celery_args = ()

        _dispatch_async(
            worker_func=_send_booking_confirmation_email_worker,
            worker_args=(request_obj, quote_obj, payment_obj),
            celery_task=celery_task,
            celery_args=celery_args
        )
        return True
    else:
        return _send_booking_confirmation_email_worker(request_obj, quote_obj, payment_obj)


def _send_booking_confirmation_email_worker(request_obj, quote_obj=None, payment_obj=None):
    recipient_user = getattr(request_obj, 'requester', None)
    recipient_email = None

    if recipient_user and recipient_user.email:
        recipient_email = recipient_user.email
    elif request_obj.customer and getattr(request_obj.customer, 'contact_email', None):
        recipient_email = request_obj.customer.contact_email
    elif request_obj.customer and getattr(request_obj.customer, 'billing_email', None):
        recipient_email = request_obj.customer.billing_email

    if not recipient_email:
        logger.warning(f"No recipient email found for booking confirmation on request {request_obj.request_number}")
        return False

    if not quote_obj:
        quote_obj = request_obj.customer_quotes.exclude(status='DECLINED').order_by('-created_at').first()

    if not payment_obj:
        payment_obj = request_obj.payments.filter(status='SUCCESSFUL').order_by('-created_at').first()

    recipient_name = recipient_user.get_full_name() if recipient_user else request_obj.customer.company_name
    site_url = getattr(settings, 'SITE_URL', 'https://flexyridegh.com').rstrip('/')
    booking_url = f"{site_url}/portal/bookings/{request_obj.request_number}/confirmed/"

    subject = f"Booking Confirmed: Transfer #{request_obj.request_number}"
    context = {
        'request': request_obj,
        'quote': quote_obj,
        'payment': payment_obj,
        'recipient_name': recipient_name,
        'booking_url': booking_url,
        'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'dispatch@flexyridegh.com'),
    }

    try:
        html_content = render_to_string('notifications/emails/booking_confirmation_email.html', context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'FlexyRide Corporate <noreply@flexyridegh.com>')
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        Notification.objects.create(
            recipient=recipient_user,
            request=request_obj,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.BOOKING_UPDATE,
            title=subject,
            message=f"Booking confirmed email dispatched to {recipient_email} for #{request_obj.request_number}.",
            delivery_status=Notification.DeliveryStatus.SENT,
            sent_at=timezone.now()
        )

        logger.info(f"Booking confirmation email sent to {recipient_email} for #{request_obj.request_number}")

        if recipient_user:
            dispatch_notification(
                user=recipient_user,
                request_obj=request_obj,
                title="Booking Confirmed",
                message=f"Journey #{request_obj.request_number} is confirmed and scheduled.",
                notification_type=Notification.NotificationType.BOOKING_UPDATE,
                url=booking_url
            )

        return True

    except Exception as e:
        logger.error(f"Failed to send booking confirmation email for #{request_obj.request_number}: {e}")
        if recipient_user:
            Notification.objects.create(
                recipient=recipient_user,
                request=request_obj,
                channel=Notification.Channel.EMAIL,
                notification_type=Notification.NotificationType.BOOKING_UPDATE,
                title=subject,
                message=f"Failed sending booking confirmation email to {recipient_email}: {str(e)}",
                delivery_status=Notification.DeliveryStatus.FAILED
            )
        return False


# ==============================================================================
# 3. Payment Receipt Email
# ==============================================================================

def send_payment_receipt_email(payment_transaction, receipt_obj=None, async_send=None):
    """
    Dispatches itemized payment receipt email to corporate client.
    Runs asynchronously in background by default.
    """
    if should_send_async(async_send):
        try:
            from notifications.tasks import send_payment_receipt_email_async
            celery_task = send_payment_receipt_email_async
            celery_args = (payment_transaction.id, receipt_obj.id if receipt_obj else None)
        except Exception:
            celery_task = None
            celery_args = ()

        _dispatch_async(
            worker_func=_send_payment_receipt_email_worker,
            worker_args=(payment_transaction, receipt_obj),
            celery_task=celery_task,
            celery_args=celery_args
        )
        return True
    else:
        return _send_payment_receipt_email_worker(payment_transaction, receipt_obj)


def _send_payment_receipt_email_worker(payment_transaction, receipt_obj=None):
    from payments.models import PaymentReceipt

    req = payment_transaction.request
    recipient_user = getattr(payment_transaction, 'paid_by', None) or getattr(req, 'requester', None)
    recipient_email = None

    if recipient_user and recipient_user.email:
        recipient_email = recipient_user.email
    elif req and req.customer and getattr(req.customer, 'billing_email', None):
        recipient_email = req.customer.billing_email
    elif req and req.customer and getattr(req.customer, 'contact_email', None):
        recipient_email = req.customer.contact_email

    if not recipient_email:
        logger.warning(f"No recipient email found for payment {payment_transaction.transaction_reference}")
        return False

    if not receipt_obj:
        receipt_obj = PaymentReceipt.objects.filter(transaction=payment_transaction).first()

    recipient_name = recipient_user.get_full_name() if recipient_user else (req.customer.company_name if req and req.customer else "Valued Client")
    site_url = getattr(settings, 'SITE_URL', 'https://flexyridegh.com').rstrip('/')
    receipt_url = f"{site_url}/portal/bookings/{req.request_number}/confirmed/" if req else f"{site_url}/portal/invoices/"

    receipt_no = receipt_obj.receipt_number if receipt_obj else payment_transaction.transaction_reference
    subject = f"Payment Receipt #{receipt_no} — {payment_transaction.currency} {payment_transaction.amount:,.2f}"

    context = {
        'payment': payment_transaction,
        'receipt': receipt_obj,
        'request': req,
        'quote': payment_transaction.customer_quote,
        'recipient_name': recipient_name,
        'receipt_url': receipt_url,
        'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'corporate@flexyridegh.com'),
    }

    try:
        html_content = render_to_string('notifications/emails/payment_receipt_email.html', context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'FlexyRide Corporate <noreply@flexyridegh.com>')
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        Notification.objects.create(
            recipient=recipient_user,
            request=req,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
            title=subject,
            message=f"Official receipt dispatched for {payment_transaction.currency} {payment_transaction.amount:,.2f} to {recipient_email}.",
            delivery_status=Notification.DeliveryStatus.SENT,
            sent_at=timezone.now()
        )

        logger.info(f"Payment receipt email sent to {recipient_email} for ref {payment_transaction.transaction_reference}")

        if recipient_user:
            dispatch_notification(
                user=recipient_user,
                request_obj=req,
                title="Payment Receipt Issued",
                message=f"Receipt #{receipt_no} issued for {payment_transaction.currency} {payment_transaction.amount:,.0f}.",
                notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
                url=receipt_url
            )

        return True

    except Exception as e:
        logger.error(f"Failed to send payment receipt email for {payment_transaction.transaction_reference}: {e}")
        if recipient_user:
            Notification.objects.create(
                recipient=recipient_user,
                request=req,
                channel=Notification.Channel.EMAIL,
                notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
                title=subject,
                message=f"Failed sending payment receipt to {recipient_email}: {str(e)}",
                delivery_status=Notification.DeliveryStatus.FAILED
            )
        return False


# ==============================================================================
# 4. Driver & Vehicle Assigned Email
# ==============================================================================

def send_driver_assigned_email(vehicle_assignment, async_send=None):
    """
    Dispatches driver and vehicle assignment notification email to passenger and requester.
    Runs asynchronously in background by default.
    """
    if should_send_async(async_send):
        try:
            from notifications.tasks import send_driver_assigned_email_async
            celery_task = send_driver_assigned_email_async
            celery_args = (vehicle_assignment.id,)
        except Exception:
            celery_task = None
            celery_args = ()

        _dispatch_async(
            worker_func=_send_driver_assigned_email_worker,
            worker_args=(vehicle_assignment,),
            celery_task=celery_task,
            celery_args=celery_args
        )
        return True
    else:
        return _send_driver_assigned_email_worker(vehicle_assignment)


def _send_driver_assigned_email_worker(vehicle_assignment):
    req = vehicle_assignment.request
    primary_pass = req.passengers.filter(is_primary=True).first() or req.passengers.first()
    requester = getattr(req, 'requester', None)

    # Collect recipient emails without duplicates
    recipient_emails = []
    if primary_pass and primary_pass.email:
        recipient_emails.append(primary_pass.email)
    if requester and requester.email and requester.email not in recipient_emails:
        recipient_emails.append(requester.email)
    if not recipient_emails and req.customer and getattr(req.customer, 'contact_email', None):
        recipient_emails.append(req.customer.contact_email)

    if not recipient_emails:
        logger.warning(f"No recipient email found for driver assignment on request {req.request_number}")
        return False

    recipient_name = primary_pass.full_name if primary_pass else (requester.get_full_name() if requester else "Valued Passenger")
    site_url = getattr(settings, 'SITE_URL', 'https://flexyridegh.com').rstrip('/')
    if primary_pass and primary_pass.tracking_token:
        tracking_url = f"{site_url}/track/{primary_pass.tracking_token}/"
    else:
        tracking_url = f"{site_url}/portal/trips/{req.request_number}/live/"

    driver_name = vehicle_assignment.driver.full_name if vehicle_assignment.driver else "Assigned Chauffeur"
    subject = f"Driver Assigned: Transfer #{req.request_number} — {driver_name}"

    context = {
        'assignment': vehicle_assignment,
        'request': req,
        'primary_passenger': primary_pass,
        'recipient_name': recipient_name,
        'tracking_url': tracking_url,
        'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'dispatch@flexyridegh.com'),
    }

    try:
        html_content = render_to_string('notifications/emails/driver_assigned_email.html', context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'FlexyRide Corporate <noreply@flexyridegh.com>')
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_emails
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        Notification.objects.create(
            recipient=requester,
            passenger_info=primary_pass,
            request=req,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.DRIVER_ASSIGNED,
            title=subject,
            message=f"Chauffeur assignment details ({driver_name}, {vehicle_assignment.vehicle.registration_number}) dispatched to {', '.join(recipient_emails)}.",
            delivery_status=Notification.DeliveryStatus.SENT,
            sent_at=timezone.now()
        )

        logger.info(f"Driver assigned email sent to {recipient_emails} for #{req.request_number}")

        if requester:
            dispatch_notification(
                user=requester,
                request_obj=req,
                title="Driver Assigned",
                message=f"Chauffeur {driver_name} with vehicle {vehicle_assignment.vehicle.registration_number} assigned to #{req.request_number}.",
                notification_type=Notification.NotificationType.DRIVER_ASSIGNED,
                url=tracking_url
            )

        return True

    except Exception as e:
        logger.error(f"Failed to send driver assigned email for #{req.request_number}: {e}")
        if requester:
            Notification.objects.create(
                recipient=requester,
                request=req,
                channel=Notification.Channel.EMAIL,
                notification_type=Notification.NotificationType.DRIVER_ASSIGNED,
                title=subject,
                message=f"Failed sending driver assignment email: {str(e)}",
                delivery_status=Notification.DeliveryStatus.FAILED
            )
        return False
