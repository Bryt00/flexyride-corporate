from django.db.models.signals import post_save
from django.dispatch import receiver
from bookings.models import TransportationRequest, VehicleAssignment
from notifications.models import Notification


@receiver(post_save, sender=TransportationRequest)
def on_booking_status_change(sender, instance, created, **kwargs):
    if created:
        # Notify requester
        Notification.objects.create(
            recipient=instance.requester,
            request=instance,
            channel=Notification.Channel.IN_APP,
            notification_type=Notification.NotificationType.BOOKING_UPDATE,
            title=f"Booking {instance.request_number} Submitted",
            message=f"Your transportation request from {instance.pickup_address} to {instance.destination_address} has been received."
        )
    else:
        # Notify on status changes
        Notification.objects.create(
            recipient=instance.requester,
            request=instance,
            channel=Notification.Channel.IN_APP,
            notification_type=Notification.NotificationType.BOOKING_UPDATE,
            title=f"Booking {instance.request_number} Updated",
            message=f"Booking status is now: {instance.get_booking_status_display()}."
        )


@receiver(post_save, sender=VehicleAssignment)
def on_vehicle_assignment(sender, instance, created, **kwargs):
    if created:
        req = instance.request
        # Notify primary passenger
        primary_pass = req.passengers.filter(is_primary=True).first()
        driver_name = instance.driver.full_name if instance.driver else "Assigned Driver"
        veh_name = f"{instance.vehicle.make} {instance.vehicle.model} ({instance.vehicle.registration_number})" if instance.vehicle else "Assigned Vehicle"
        
        msg = f"Driver {driver_name} with vehicle {veh_name} has been assigned to trip {req.request_number}."
        
        if primary_pass and primary_pass.email:
            Notification.objects.create(
                passenger_info=primary_pass,
                request=req,
                channel=Notification.Channel.SMS,
                notification_type=Notification.NotificationType.DRIVER_ASSIGNED,
                title=f"Driver Assigned - {req.request_number}",
                message=msg
            )
