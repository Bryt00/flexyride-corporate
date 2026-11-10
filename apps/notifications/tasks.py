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


@shared_task(name='notifications.send_rfq_invitation_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_rfq_invitation_email_async(self, provider_id, request_id):
    """Asynchronous Celery worker task to dispatch provider RFQ tender invitation email."""
    from accounts.models import ProviderCompany
    from bookings.models import TransportationRequest
    from notifications.email_service import _send_rfq_invitation_email_worker

    try:
        provider = ProviderCompany.objects.get(id=provider_id)
        req = TransportationRequest.objects.get(id=request_id)
        return _send_rfq_invitation_email_worker(provider, req)
    except Exception as exc:
        logger.error(f"Error in send_rfq_invitation_email_async task: {exc}")
        raise self.retry(exc=exc)


@shared_task(name='notifications.send_ride_reminder_email_async', bind=True, max_retries=3, default_retry_delay=60)
def send_ride_reminder_email_async(self, request_id, reminder_type='2h'):
    """Asynchronous Celery worker task to dispatch scheduled ride reminder email."""
    from bookings.models import TransportationRequest
    from notifications.email_service import _send_ride_reminder_email_worker

    try:
        req = TransportationRequest.objects.get(id=request_id)
        return _send_ride_reminder_email_worker(req, reminder_type)
    except Exception as exc:
        logger.error(f"Error in send_ride_reminder_email_async task: {exc}")
        raise self.retry(exc=exc)


@shared_task(name='notifications.dispatch_ride_reminders_task')
def dispatch_ride_reminders_task():
    """
    Periodic background job (Celery Beat) running every 5 minutes.
    Scans upcoming confirmed/assigned scheduled rides and dispatches:
    - 2-hour pre-trip reminder email if within the 2-hour window and not yet sent.
    - 1-hour pre-trip reminder email if within the 1-hour window and not yet sent.
    """
    from datetime import timedelta
    from django.utils import timezone
    from bookings.models import TransportationRequest
    from notifications.email_service import send_ride_reminder_email

    now = timezone.now()
    active_statuses = [
        TransportationRequest.BookingStatus.CONFIRMED,
        TransportationRequest.BookingStatus.ASSIGNED,
        TransportationRequest.BookingStatus.DRIVER_EN_ROUTE,
    ]

    results = {
        'timestamp': now.isoformat(),
        'reminders_2h_sent': 0,
        'reminders_1h_sent': 0,
        'processed_requests': [],
    }

    # 1. Check for 2-Hour Reminders
    # Target window: between 1h15m and 2h15m ahead
    two_hours_min = now + timedelta(minutes=75)
    two_hours_max = now + timedelta(hours=2, minutes=15)

    rides_2h = TransportationRequest.objects.filter(
        booking_status__in=active_statuses,
        departure_datetime__gte=two_hours_min,
        departure_datetime__lte=two_hours_max,
        reminder_2h_sent_at__isnull=True
    ).order_by('departure_datetime')

    for ride in rides_2h:
        try:
            logger.info(f"[RideReminder] Dispatching 2-hour reminder for ride #{ride.request_number} (departure {ride.departure_datetime})")
            send_ride_reminder_email(ride, reminder_type='2h', async_send=False)
            results['reminders_2h_sent'] += 1
            results['processed_requests'].append(f"{ride.request_number} (2h)")
        except Exception as e:
            logger.error(f"[RideReminder] Error sending 2h reminder for #{ride.request_number}: {e}")

    # 2. Check for 1-Hour Reminders
    # Target window: between now and 1h15m ahead
    one_hour_min = now
    one_hour_max = now + timedelta(hours=1, minutes=15)

    rides_1h = TransportationRequest.objects.filter(
        booking_status__in=active_statuses,
        departure_datetime__gte=one_hour_min,
        departure_datetime__lte=one_hour_max,
        reminder_1h_sent_at__isnull=True
    ).order_by('departure_datetime')

    for ride in rides_1h:
        try:
            logger.info(f"[RideReminder] Dispatching 1-hour reminder for ride #{ride.request_number} (departure {ride.departure_datetime})")
            send_ride_reminder_email(ride, reminder_type='1h', async_send=False)
            results['reminders_1h_sent'] += 1
            results['processed_requests'].append(f"{ride.request_number} (1h)")
        except Exception as e:
            logger.error(f"[RideReminder] Error sending 1h reminder for #{ride.request_number}: {e}")

    logger.info(
        f"[RideReminder] Completed check: {results['reminders_2h_sent']} 2h reminders, {results['reminders_1h_sent']} 1h reminders dispatched."
    )
    return results


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


