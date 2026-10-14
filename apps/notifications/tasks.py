"""Celery background tasks for notifications application."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name='notifications.send_quote_ready_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_quote_ready_email_async(self, quote_id, request_id):
    """Asynchronous Celery worker task to dispatch quote ready email."""
    from quotations.models import CustomerQuote
    from bookings.models import TransportationRequest
    from notifications.email_service import _send_quote_ready_email_worker

    try:
        quote = CustomerQuote.objects.get(id=quote_id)
        req = TransportationRequest.objects.get(id=request_id)
        return _send_quote_ready_email_worker(quote, req)
    except Exception as exc:
        logger.error(f"Error in send_quote_ready_email_async task: {exc}")
        raise self.retry(exc=exc)


@shared_task(name='notifications.send_booking_confirmation_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_booking_confirmation_email_async(self, request_id, quote_id=None, payment_id=None):
    """Asynchronous Celery worker task to dispatch booking confirmation email."""
    from bookings.models import TransportationRequest
    from quotations.models import CustomerQuote
    from payments.models import PaymentTransaction
    from notifications.email_service import _send_booking_confirmation_email_worker

    try:
        req = TransportationRequest.objects.get(id=request_id)
        quote = CustomerQuote.objects.get(id=quote_id) if quote_id else None
        payment = PaymentTransaction.objects.get(id=payment_id) if payment_id else None
        return _send_booking_confirmation_email_worker(req, quote, payment)
    except Exception as exc:
        logger.error(f"Error in send_booking_confirmation_email_async task: {exc}")
        raise self.retry(exc=exc)


@shared_task(name='notifications.send_payment_receipt_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_payment_receipt_email_async(self, payment_id, receipt_id=None):
    """Asynchronous Celery worker task to dispatch payment receipt email."""
    from payments.models import PaymentTransaction, PaymentReceipt
    from notifications.email_service import _send_payment_receipt_email_worker

    try:
        payment = PaymentTransaction.objects.get(id=payment_id)
        receipt = PaymentReceipt.objects.get(id=receipt_id) if receipt_id else getattr(payment, 'receipt', None)
        return _send_payment_receipt_email_worker(payment, receipt)
    except Exception as exc:
        logger.error(f"Error in send_payment_receipt_email_async task: {exc}")
        raise self.retry(exc=exc)


@shared_task(name='notifications.send_driver_assigned_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_driver_assigned_email_async(self, assignment_id):
    """Asynchronous Celery worker task to dispatch driver assigned email."""
    from bookings.models import VehicleAssignment
    from notifications.email_service import _send_driver_assigned_email_worker

    try:
        assignment = VehicleAssignment.objects.get(id=assignment_id)
        return _send_driver_assigned_email_worker(assignment)
    except Exception as exc:
        logger.error(f"Error in send_driver_assigned_email_async task: {exc}")
        raise self.retry(exc=exc)


@shared_task(name='notifications.send_provider_welcome_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_provider_welcome_email_async(self, provider_id, user_id, temp_password=None):
    """Asynchronous Celery worker task to dispatch provider welcome credentials email."""
    from accounts.models import ProviderCompany, User
    from notifications.email_service import _send_provider_welcome_email_worker

    try:
        provider = ProviderCompany.objects.get(id=provider_id)
        user = User.objects.get(id=user_id)
        return _send_provider_welcome_email_worker(provider, user, temp_password)
    except Exception as exc:
        logger.error(f"Error in send_provider_welcome_email_async task: {exc}")
        raise self.retry(exc=exc)


def run_campaign_dispatch(campaign_id: int):
    """Executes campaign broadcast across specified channels (Email, SMS, Push)."""
    from django.utils import timezone
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.conf import settings
    from notifications.models import Notification, NotificationCampaign
    from notifications.sms_service import sms_service
    from notifications.webpush import dispatch_notification

    try:
        campaign = NotificationCampaign.objects.get(pk=campaign_id)
    except NotificationCampaign.DoesNotExist:
        logger.error(f"[Campaign] Campaign ID {campaign_id} not found.")
        return

    campaign.status = NotificationCampaign.Status.SENDING
    campaign.save(update_fields=['status'])

    recipients = campaign.get_recipients()
    campaign.total_recipients = len(recipients)
    campaign.save(update_fields=['total_recipients'])

    successful = 0
    failed = 0
    errors = []

    channel = campaign.channel
    send_email = channel in (
        NotificationCampaign.Channel.EMAIL,
        NotificationCampaign.Channel.EMAIL_AND_SMS,
        NotificationCampaign.Channel.ALL
    )
    send_sms = channel in (
        NotificationCampaign.Channel.SMS,
        NotificationCampaign.Channel.EMAIL_AND_SMS,
        NotificationCampaign.Channel.ALL
    )
    send_push = channel in (
        NotificationCampaign.Channel.PUSH,
        NotificationCampaign.Channel.ALL
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'FlexyRide Operations <operations@flexyridegh.com>')

    for rec in recipients:
        name = rec.get('name') or 'Valued Customer'
        company = rec.get('company') or ''
        email = rec.get('email')
        phone = rec.get('phone')
        user = rec.get('user')

        personalized_text = campaign.message_body
        personalized_text = personalized_text.replace('{{name}}', name)
        personalized_text = personalized_text.replace('{{company}}', company)
        personalized_text = personalized_text.replace('{{date}}', timezone.now().strftime('%Y-%m-%d'))

        rec_success = False

        # 1. Dispatch Email
        if send_email and email:
            try:
                html_content = render_to_string(
                    'notifications/emails/campaign_broadcast_email.html',
                    {
                        'campaign': campaign,
                        'recipient_name': name,
                        'personalized_body': personalized_text,
                        'current_year': timezone.now().year,
                    }
                )
                text_content = strip_tags(personalized_text)
                msg = EmailMultiAlternatives(
                    subject=campaign.title,
                    body=text_content,
                    from_email=from_email,
                    to=[email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)

                Notification.objects.create(
                    recipient=user,
                    channel=Notification.Channel.EMAIL,
                    notification_type=Notification.NotificationType.CAMPAIGN,
                    title=campaign.title,
                    message=personalized_text,
                    delivery_status=Notification.DeliveryStatus.DELIVERED,
                    sent_at=timezone.now()
                )
                rec_success = True
            except Exception as e:
                logger.warning(f"[Campaign Email Error] Failed sending to {email}: {e}")
                errors.append(f"Email {email}: {str(e)[:100]}")

        # 2. Dispatch SMS
        if send_sms and phone:
            try:
                sms_res = sms_service.send_sms(phone, f"{campaign.title}: {personalized_text}")
                if sms_res.get('success'):
                    Notification.objects.create(
                        recipient=user,
                        channel=Notification.Channel.SMS,
                        notification_type=Notification.NotificationType.CAMPAIGN,
                        title=campaign.title,
                        message=personalized_text,
                        delivery_status=Notification.DeliveryStatus.SENT,
                        sent_at=timezone.now()
                    )
                    rec_success = True
                else:
                    errors.append(f"SMS {phone}: {sms_res.get('message', 'Failed')[:100]}")
            except Exception as e:
                logger.warning(f"[Campaign SMS Error] Failed sending to {phone}: {e}")
                errors.append(f"SMS {phone}: {str(e)[:100]}")

        # 3. Dispatch Web Push
        if send_push and user:
            try:
                dispatch_notification(
                    user=user,
                    title=campaign.title,
                    message=personalized_text[:160],
                    notification_type=Notification.NotificationType.CAMPAIGN,
                    url=campaign.action_url
                )
                rec_success = True
            except Exception as e:
                logger.warning(f"[Campaign Push Error] Failed pushing to user {user}: {e}")

        if rec_success:
            successful += 1
        else:
            failed += 1

    campaign.successful_count = successful
    campaign.failed_count = failed
    campaign.sent_at = timezone.now()
    campaign.status = NotificationCampaign.Status.SENT if (successful > 0 or len(recipients) == 0) else NotificationCampaign.Status.FAILED
    campaign.error_summary = "\n".join(errors[:20])
    campaign.save(update_fields=['successful_count', 'failed_count', 'sent_at', 'status', 'error_summary'])
    logger.info(f"[Campaign] Dispatched campaign '{campaign.title}' - {successful} succeeded, {failed} failed.")
    return {"successful": successful, "failed": failed}


@shared_task(name='notifications.dispatch_campaign_task', bind=True, max_retries=1)
def dispatch_campaign_task(self, campaign_id: int):
    """Celery worker task to dispatch campaign broadcast."""
    try:
        return run_campaign_dispatch(campaign_id)
    except Exception as exc:
        logger.error(f"Error in dispatch_campaign_task: {exc}")
        raise self.retry(exc=exc)


