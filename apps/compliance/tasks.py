"""
Celery background tasks for Compliance app.
Monitors compliance document validity, issues 30/15/7 day notices, and applies automated lockout (US-91, US-92, US-109, US-110).
"""

import logging
from celery import shared_task
from django.utils import timezone
from compliance.models import ComplianceDocument
from notifications.models import Notification
from notifications.webpush import dispatch_notification

logger = logging.getLogger(__name__)

NOTICE_INTERVALS = [30, 15, 7, 1]


@shared_task(name="compliance.tasks.check_document_expirations_task")
def check_document_expirations_task():
    """
    Daily scan of compliance documents:
    - Issues proactive renewal alerts at 30, 15, 7, and 1 days before expiration.
    - Marks past-due documents as EXPIRED to enforce automatic dispatch lockout.
    """
    today = timezone.now().date()
    notices_sent = 0
    expired_lockouts = 0

    docs = ComplianceDocument.objects.select_related('provider', 'vehicle', 'driver').exclude(
        status=ComplianceDocument.Status.REJECTED
    ).exclude(expiry_date__isnull=True)

    for doc in docs:
        days_left = (doc.expiry_date - today).days

        # 1. Past due -> Mark EXPIRED and trigger lockout
        if days_left < 0:
            if doc.status != ComplianceDocument.Status.EXPIRED:
                doc.status = ComplianceDocument.Status.EXPIRED
                doc.save(update_fields=['status'])
                expired_lockouts += 1

                target_name = (
                    doc.vehicle.registration_number if doc.vehicle else
                    doc.driver.full_name if doc.driver else
                    doc.provider.company_name if doc.provider else "Fleet Resource"
                )

                # Send emergency lockout notification to provider users
                recipients = []
                if doc.provider:
                    recipients = list(doc.provider.users.all())

                for u in recipients:
                    dispatch_notification(
                        user=u,
                        title="Compliance Lockout Triggered",
                        message=f"🚨 {doc.get_document_type_display()} for {target_name} has EXPIRED. This unit is automatically blocked from dispatch assignments.",
                        notification_type=Notification.NotificationType.COMPLIANCE_EXPIRY,
                        url="/portal/provider/compliance/"
                    )
                logger.warning("Compliance lockout applied to %s (%s)", target_name, doc.get_document_type_display())

        # 2. Upcoming expiration -> Issue 30/15/7/1 day warnings
        elif days_left in NOTICE_INTERVALS or (days_left <= 30 and doc.status == ComplianceDocument.Status.APPROVED):
            if doc.status != ComplianceDocument.Status.EXPIRING_SOON:
                doc.status = ComplianceDocument.Status.EXPIRING_SOON
                doc.save(update_fields=['status'])

            target_name = (
                doc.vehicle.registration_number if doc.vehicle else
                doc.driver.full_name if doc.driver else
                doc.provider.company_name if doc.provider else "Resource"
            )

            recipients = []
            if doc.provider:
                recipients = list(doc.provider.users.all())

            for u in recipients:
                dispatch_notification(
                    user=u,
                    title="Compliance Expiration Notice",
                    message=f"⚠️ {doc.get_document_type_display()} for {target_name} expires in {days_left} days ({doc.expiry_date}). Please upload renewal to prevent dispatch lockout.",
                    notification_type=Notification.NotificationType.COMPLIANCE_EXPIRY,
                    url="/portal/provider/compliance/"
                )
            notices_sent += 1
            logger.info("Compliance renewal notice sent for %s (%d days left)", target_name, days_left)

    return {
        "status": "success",
        "notices_sent": notices_sent,
        "expired_lockouts": expired_lockouts
    }
