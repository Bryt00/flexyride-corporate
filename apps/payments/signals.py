from django.db.models.signals import post_save
from django.dispatch import receiver
from payments.models import PaymentTransaction, PaymentReceipt
from notifications.models import Notification


@receiver(post_save, sender=PaymentTransaction)
def on_payment_status_change(sender, instance, created, **kwargs):
    if instance.status == PaymentTransaction.Status.SUCCESSFUL:
        # Ensure receipt exists
        PaymentReceipt.objects.get_or_create(transaction=instance)
        # Notify user
        Notification.objects.create(
            recipient=instance.paid_by,
            request=instance.request,
            channel=Notification.Channel.IN_APP,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
            title=f"Payment Confirmed - {instance.transaction_reference}",
            message=f"Payment of {instance.currency} {instance.amount:,} for booking {instance.request.request_number} was successful."
        )
