"""
Celery background tasks for SLA app.
Monitors operational SLA compliance, detects response time and dispatch breaches, and alerts broker mission control (US-99, US-100, US-103, US-105).
"""

import logging
from decimal import Decimal
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from quotations.models import ProviderQuoteRequest
from bookings.models import TransportationRequest, VehicleAssignment
from feedback.models import SupportIssue, BookingTimeline
from sla.models import SLAMetric
from accounts.models import User
from notifications.models import Notification
from notifications.webpush import dispatch_notification

logger = logging.getLogger(__name__)


@shared_task(name="sla.tasks.detect_sla_breaches_task")
def detect_sla_breaches_task():
    """
    Periodically evaluates operational SLAs:
    1. RFQ Response Time: Flags provider RFQs pending > 2 hours.
    2. Imminent Unassigned Missions: Flags confirmed bookings within 2 hours of departure lacking vehicle assignment.
    3. Delayed En-Route Chauffeurs: Flags assignments still marked EN_ROUTE past scheduled pickup time.
    """
    now = timezone.now()
    today = now.date()
    breaches_detected = 0

    # Find brokers and admins for escalation
    brokers = list(User.objects.filter(role__in=[User.Role.BROKER, User.Role.SYSTEM_ADMIN]))

    # --------------------------------------------------------------------------
    # 1. RFQ Quote Response Timeout (> 2 Hours)
    # --------------------------------------------------------------------------
    rfq_threshold = now - timedelta(hours=2)
    slow_rfqs = ProviderQuoteRequest.objects.select_related('provider', 'request').filter(
        status='SENT',
        requested_at__lte=rfq_threshold
    )

    for rfq in slow_rfqs:
        breaches_detected += 1
        minutes_elapsed = int((now - rfq.requested_at).total_seconds() / 60)


        # Record SLA Metric for provider
        SLAMetric.objects.create(
            provider=rfq.provider,
            metric_type=SLAMetric.MetricType.RESPONSE_TIME,
            value=Decimal(str(minutes_elapsed)),
            period_start=today.replace(day=1),
            period_end=today
        )

        # Notify broker desk
        for b in brokers:
            dispatch_notification(
                user=b,
                request_obj=rfq.request,
                title="SLA Breach: RFQ Response Overdue",
                message=f"Provider {rfq.provider.company_name} has not responded to RFQ for {rfq.request.request_number} after {minutes_elapsed} minutes (SLA: 120 mins).",
                notification_type=Notification.NotificationType.SYSTEM,
                url="/portal/broker/rfqs/"
            )
        logger.warning("SLA RFQ response timeout on request %s for %s", rfq.request.request_number, rfq.provider.company_name)

    # --------------------------------------------------------------------------
    # 2. Imminent Confirmed Missions without Vehicle/Driver Assignment (< 2 Hours)
    # --------------------------------------------------------------------------
    imminent_threshold = now + timedelta(hours=2)
    unassigned_urgent = TransportationRequest.objects.filter(
        booking_status=TransportationRequest.BookingStatus.CONFIRMED,
        departure_datetime__lte=imminent_threshold,
        departure_datetime__gte=now,
        vehicle_assignments__isnull=True
    ).distinct()

    for req in unassigned_urgent:
        breaches_detected += 1
        hours_to_pickup = round((req.departure_datetime - now).total_seconds() / 3600, 1)

        # Log timeline
        BookingTimeline.objects.get_or_create(
            request=req,
            action_type='NOTE_ADDED',
            description=f"SLA Critical Warning: Mission unassigned with only {hours_to_pickup} hours until pickup."
        )

        for b in brokers:
            dispatch_notification(
                user=b,
                request_obj=req,
                title="🚨 Urgent: Unassigned Mission",
                message=f"Trip {req.request_number} departs in {hours_to_pickup}h ({req.departure_datetime.strftime('%H:%M')}) but has NO assigned chauffeur or vehicle!",
                notification_type=Notification.NotificationType.APPROVAL_REQUIRED,
                url="/portal/broker/dispatches/"
            )
        logger.error("SLA Critical Breach: Unassigned journey %s departs in %sh", req.request_number, hours_to_pickup)

    # --------------------------------------------------------------------------
    # 3. Delayed Chauffeurs: Still EN_ROUTE past Scheduled Departure
    # --------------------------------------------------------------------------
    delayed_assignments = VehicleAssignment.objects.select_related('request', 'driver', 'vehicle').filter(
        status=VehicleAssignment.Status.EN_ROUTE,
        request__departure_datetime__lt=now - timedelta(minutes=15)
    )

    for va in delayed_assignments:
        req = va.request
        breaches_detected += 1
        mins_delayed = int((now - req.departure_datetime).total_seconds() / 60)

        # Log support issue if not already created
        issue, created = SupportIssue.objects.get_or_create(
            request=req,
            issue_type='NO_SHOW',
            defaults={
                'description': f"Automated SLA Alert: Chauffeur {va.driver.full_name} is still EN_ROUTE {mins_delayed} minutes past scheduled pickup.",
                'status': SupportIssue.Status.OPEN
            }
        )

        if created:
            for b in brokers:
                dispatch_notification(
                    user=b,
                    request_obj=req,
                    title="Chauffeur Arrival Delay",
                    message=f"Mission {req.request_number} chauffeur is {mins_delayed} mins late past pickup time {req.departure_datetime.strftime('%H:%M')}.",
                    notification_type=Notification.NotificationType.BOOKING_UPDATE,
                    url=f"/portal/bookings/{req.request_number}/track/"
                )
            logger.warning("Delayed arrival detected on %s: %d mins", req.request_number, mins_delayed)

    return {
        "status": "success",
        "breaches_detected": breaches_detected,
        "slow_rfqs_count": slow_rfqs.count(),
        "unassigned_urgent_count": unassigned_urgent.count(),
        "delayed_chauffeurs_count": delayed_assignments.count()
    }
