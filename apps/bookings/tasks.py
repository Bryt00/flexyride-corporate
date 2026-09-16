"""
Celery background tasks for Bookings app.
Handles automated recurring transportation booking occurrences (US-11, US-103).
"""

import uuid
import logging
from datetime import timedelta, datetime
from celery import shared_task
from django.utils import timezone
from bookings.models import TransportationRequest, RecurringSchedule, PassengerInfo
from feedback.models import BookingTimeline
from notifications.models import Notification
from notifications.webpush import dispatch_notification

logger = logging.getLogger(__name__)

DAY_CODE_MAP = {
    0: 'MON',
    1: 'TUE',
    2: 'WED',
    3: 'THU',
    4: 'FRI',
    5: 'SAT',
    6: 'SUN'
}


@shared_task(name="bookings.tasks.generate_recurring_bookings_task")
def generate_recurring_bookings_task(days_ahead: int = 7):
    """
    Scans active recurring schedules and generates concrete TransportationRequest
    journey occurrences for the upcoming days.
    """
    today = timezone.now().date()
    horizon = today + timedelta(days=days_ahead)
    generated = []

    schedules = RecurringSchedule.objects.select_related('request', 'request__customer', 'request__requester').filter(
        start_date__lte=horizon,
        end_date__gte=today
    )

    for schedule in schedules:
        template = schedule.request
        allowed_days = [d.strip().upper() for d in schedule.days_of_week.split(',') if d.strip()]

        current_date = max(today, schedule.start_date)
        end_date = min(horizon, schedule.end_date)

        while current_date <= end_date:
            day_code = DAY_CODE_MAP.get(current_date.weekday())
            if schedule.frequency == RecurringSchedule.Frequency.DAILY or day_code in allowed_days:
                # Combine current date with template request departure time
                orig_time = template.departure_datetime.time() if template.departure_datetime else datetime.min.time()
                occurrence_departure = timezone.make_aware(
                    datetime.combine(current_date, orig_time),
                    timezone.get_current_timezone()
                )

                # Skip if already in the past
                if occurrence_departure <= timezone.now():
                    current_date += timedelta(days=1)
                    continue

                # Check if this occurrence already exists
                exists = TransportationRequest.objects.filter(
                    customer=template.customer,
                    pickup_address=template.pickup_address,
                    destination_address=template.destination_address,
                    departure_datetime=occurrence_departure
                ).exists()

                if not exists:
                    new_ref = f"FRC-R{uuid.uuid4().hex[:7].upper()}"
                    new_request = TransportationRequest.objects.create(
                        customer=template.customer,
                        requester=template.requester,
                        request_number=new_ref,
                        journey_type=template.journey_type,
                        requested_vehicle_category=template.requested_vehicle_category,
                        vehicles_requested_count=template.vehicles_requested_count,
                        pickup_address=template.pickup_address,
                        destination_address=template.destination_address,
                        departure_datetime=occurrence_departure,
                        return_datetime=occurrence_departure + timedelta(hours=2) if template.return_datetime else None,
                        duration_hours=template.duration_hours,
                        passenger_count=template.passenger_count,
                        luggage_requirements=template.luggage_requirements,
                        accessibility_required=template.accessibility_required,
                        child_seats_count=template.child_seats_count,
                        executive_vehicle_required=template.executive_vehicle_required,
                        additional_stops_notes=template.additional_stops_notes,
                        booking_status=TransportationRequest.BookingStatus.RECEIVED_BY_FLEXYRIDE,
                        estimated_distance_km=template.estimated_distance_km
                    )

                    # Clone passengers
                    for p in template.passengers.all():
                        PassengerInfo.objects.create(
                            request=new_request,
                            full_name=p.full_name,
                            phone_number=p.phone_number,
                            email=p.email,
                            is_primary=p.is_primary
                        )

                    # Log timeline
                    BookingTimeline.objects.create(
                        request=new_request,
                        action_type='STATUS_CHANGE',
                        previous_status='DRAFT',
                        new_status='RECEIVED_BY_FLEXYRIDE',
                        actor=template.requester,
                        description=f"Generated automatically from recurring schedule #{schedule.id} ({schedule.frequency})."
                    )

                    # Dispatch notification
                    if template.requester:
                        dispatch_notification(
                            user=template.requester,
                            request_obj=new_request,
                            title="Recurring Mission Scheduled",
                            message=f"Upcoming recurring mission {new_request.request_number} scheduled for {occurrence_departure.strftime('%b %d, %H:%M')}.",
                            notification_type=Notification.NotificationType.BOOKING_UPDATE,
                            url=f"/portal/requests/{new_request.request_number}/details/"
                        )

                    generated.append(new_request.request_number)
                    logger.info("Generated recurring request %s for %s", new_ref, occurrence_departure)

            current_date += timedelta(days=1)

    return {"status": "success", "generated_count": len(generated), "requests": generated}
