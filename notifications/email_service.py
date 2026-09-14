"""
Email Service for FlexyRide Corporate.
Dispatches branded transactional emails (Quotes, Confirmations, Receipts)
and records notification audit history.
"""

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from notifications.models import Notification
from notifications.webpush import dispatch_notification

logger = logging.getLogger(__name__)


def send_quote_ready_email(customer_quote, request_obj):
    """
    Dispatches official quote ready notification email to corporate client
    and records in-app & web push notifications.
    """
    recipient_user = getattr(request_obj, 'requester', None)
    recipient_email = None

    if recipient_user and recipient_user.email:
        recipient_email = recipient_user.email
    elif request_obj.customer and getattr(request_obj.customer, 'contact_email', None):
        recipient_email = request_obj.customer.contact_email
    elif request_obj.customer and getattr(request_obj.customer, 'billing_email', None):
        recipient_email = request_obj.customer.billing_email

    if not recipient_email:
        logger.warning(f"No recipient email found for request {request_obj.request_number}")
        return False

    recipient_name = recipient_user.get_full_name() if recipient_user else request_obj.customer.company_name
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
    auth_url = f"{site_url}/portal/quotes/{request_obj.request_number}/"

    subject = f"Quote Ready: Transfer #{request_obj.request_number} — GHS {customer_quote.final_customer_price:,.2f}"
    context = {
        'request': request_obj,
        'quote': customer_quote,
        'recipient_name': recipient_name,
        'authorization_url': auth_url,
    }

    try:
        html_content = render_to_string('portal/emails/quote_ready_email.html', context)
        text_content = strip_tags(html_content)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'FlexyRide Corporate <dispatch@flexyride.com>')
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

        # Also push in-app / browser notification
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
        # Log failure audit record
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
