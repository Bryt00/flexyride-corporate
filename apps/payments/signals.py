from django.db.models.signals import post_save
from django.dispatch import receiver
from payments.models import PaymentTransaction, PaymentReceipt
from notifications.models import Notification


@receiver(post_save, sender=PaymentTransaction)
def on_payment_status_change(sender, instance, created, **kwargs):
    if instance.status == PaymentTransaction.Status.SUCCESSFUL:
        # Ensure receipt exists
        receipt, _ = PaymentReceipt.objects.get_or_create(transaction=instance)

        # Record in-app notification
        if not Notification.objects.filter(
            recipient=instance.paid_by,
            request=instance.request,
            channel=Notification.Channel.IN_APP,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED
        ).exists():
            Notification.objects.create(
                recipient=instance.paid_by,
                request=instance.request,
                channel=Notification.Channel.IN_APP,
                notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
                title=f"Payment Confirmed - {instance.transaction_reference}",
                message=f"Payment of {instance.currency} {instance.amount:,} for booking {instance.request.request_number} was successful."
            )

        # Dispatch payment receipt & booking confirmation emails (idempotent)
        already_dispatched = Notification.objects.filter(
            request=instance.request,
            channel=Notification.Channel.EMAIL,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED
        ).exists()

        if not already_dispatched:
            from notifications.email_service import send_payment_receipt_email, send_booking_confirmation_email
            send_payment_receipt_email(instance, receipt)
            send_booking_confirmation_email(instance.request, instance.customer_quote, instance)
