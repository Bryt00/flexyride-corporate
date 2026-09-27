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
