"""
Celery background tasks for Compliance app.
Monitors compliance document validity, issues 30/14/7/0 day notices, logs audit trails,
and applies automated lockout & booking review flags (Paystack Compliance Section 7).
"""

import logging
from celery import shared_task
from django.utils import timezone
from compliance.models import ComplianceDocument, ComplianceAuditLog
from accounts.models import User, ProviderCompany
from fleet.models import Vehicle
from bookings.models import VehicleAssignment
from notifications.models import Notification
from notifications.webpush import dispatch_notification

logger = logging.getLogger(__name__)

NOTICE_INTERVALS = [30, 14, 7, 0]


@shared_task(name="compliance.tasks.check_document_expirations_task")
def check_document_expirations_task():
    """
    Daily automated compliance scan:
    - Alerts at 30, 14, 7, and 0 days prior to expiration.
    - Transitions past-due documents to EXPIRED.
    - Applies vehicle / provider compliance lockout.
    - Flags existing confirmed bookings for review.
    - Records actions in ComplianceAuditLog.
    """
    today = timezone.now().date()
    notices_sent = 0
    expired_lockouts = 0

    docs = ComplianceDocument.objects.select_related('provider', 'vehicle', 'driver').exclude(
        status=ComplianceDocument.Status.REJECTED
    ).exclude(expiry_date__isnull=True)

    broker_admins = list(User.objects.filter(role__in=[User.Role.BROKER, User.Role.SYSTEM_ADMIN], is_active=True))

    for doc in docs:
        if not doc.expiry_date:
            continue

        days_left = (doc.expiry_date - today).days

        # 1. Past due or day-of expiry -> Mark EXPIRED and trigger lockout
        if days_left <= 0:
            if doc.status != ComplianceDocument.Status.EXPIRED:
                prev_status = doc.status
                doc.status = ComplianceDocument.Status.EXPIRED
                doc.save(update_fields=['status', 'updated_at'])
                expired_lockouts += 1

                target_name = (
                    f"Vehicle {doc.vehicle.registration_number}" if doc.vehicle else
                    f"Chauffeur {doc.driver.full_name}" if doc.driver else
                    f"Provider {doc.provider.company_name}" if doc.provider else "Fleet Resource"
                )

                # Lockout Vehicle
                if doc.vehicle:
                    doc.vehicle.compliance_status = 'EXPIRED'
                    doc.vehicle.save(update_fields=['compliance_status'])

                    # Flag existing confirmed assignments for admin review & reassignment
                    active_assignments = VehicleAssignment.objects.filter(
                        vehicle=doc.vehicle,
                        status__in=['ASSIGNED', 'EN_ROUTE', 'ARRIVED']
                    ).select_related('request')
                    for assign in active_assignments:
                        flag_note = f"[COMPLIANCE EXPIRED] Vehicle {doc.vehicle.registration_number} roadworthiness/document expired on {doc.expiry_date}. Flagged for review & reassignment."
                        if assign.replacement_reason:
                            assign.replacement_reason += f"\n{flag_note}"
                        else:
                            assign.replacement_reason = flag_note
                        assign.save(update_fields=['replacement_reason'])

                # Lockout Provider if Operator Licence expired
                if doc.provider and doc.document_type in ['OPERATOR_LICENSE', 'BUSINESS_LICENSE']:
                    doc.provider.status = ProviderCompany.Status.SUSPENDED
                    doc.provider.save(update_fields=['status', 'updated_at'])

                    # Also flag all vehicles under this provider
                    doc.provider.vehicles.update(compliance_status='EXPIRED')

                    # Flag existing bookings
                    provider_assignments = VehicleAssignment.objects.filter(
                        vehicle__provider=doc.provider,
                        status__in=['ASSIGNED', 'EN_ROUTE', 'ARRIVED']
                    ).select_related('request')
                    for assign in provider_assignments:
                        flag_note = f"[COMPLIANCE SUSPENSION] Provider {doc.provider.company_name} operator licence expired on {doc.expiry_date}. Flagged for review & reassignment."
                        if assign.replacement_reason:
                            assign.replacement_reason += f"\n{flag_note}"
                        else:
                            assign.replacement_reason = flag_note
                        assign.save(update_fields=['replacement_reason'])

                # Record in ComplianceAuditLog
                ComplianceAuditLog.log_action(
                    action=ComplianceAuditLog.Action.EXPIRY_DETECTED,
                    actor=None,
                    provider=doc.provider,
                    vehicle=doc.vehicle,
                    document=doc,
                    previous_status=prev_status,
                    new_status=ComplianceDocument.Status.EXPIRED,
                    notes=f"Automated expiry scan: {doc.get_document_type_display()} expired on {doc.expiry_date}. Dispatched lockout & flagged active bookings."
                )

                # Notify Provider Users
                provider_users = (
                    list(User.objects.filter(role=User.Role.PROVIDER_ADMIN, email=doc.provider.email, is_active=True))
                    if (doc.provider and doc.provider.email)
                    else []
                )
                for u in provider_users:
                    dispatch_notification(
                        user=u,
                        title="🚨 Compliance Lockout Enforced",
                        message=f"{doc.get_document_type_display()} for {target_name} has EXPIRED ({doc.expiry_date}). Bookings are blocked until renewed.",
                        notification_type=Notification.NotificationType.COMPLIANCE_EXPIRY,
                        url="/portal/provider/compliance/"
                    )

                # Notify Super Admins / Brokers
                for admin_user in broker_admins:
                    dispatch_notification(
                        user=admin_user,
                        title="🚨 Provider Compliance Expiry",
                        message=f"{target_name} document expired ({doc.get_document_type_display()}). Affected bookings flagged for review.",
                        notification_type=Notification.NotificationType.COMPLIANCE_EXPIRY,
                        url="/portal/broker/compliance/"
                    )

                logger.warning("Compliance lockout applied to %s (%s)", target_name, doc.get_document_type_display())

        # 2. Upcoming expiration -> Issue 30/14/7 day warnings
        elif days_left in NOTICE_INTERVALS or (days_left <= 30 and doc.status in (ComplianceDocument.Status.VERIFIED, 'APPROVED')):
            if doc.status != ComplianceDocument.Status.EXPIRING_SOON:
                prev_status = doc.status
                doc.status = ComplianceDocument.Status.EXPIRING_SOON
                doc.save(update_fields=['status'])

                ComplianceAuditLog.log_action(
                    action=ComplianceAuditLog.Action.EXPIRY_DETECTED,
                    actor=None,
                    provider=doc.provider,
                    vehicle=doc.vehicle,
                    document=doc,
                    previous_status=prev_status,
                    new_status=ComplianceDocument.Status.EXPIRING_SOON,
                    notes=f"Document approaching expiry in {days_left} days ({doc.expiry_date}). Flagged as Expiring Soon."
                )

            target_name = (
                f"Vehicle {doc.vehicle.registration_number}" if doc.vehicle else
                f"Chauffeur {doc.driver.full_name}" if doc.driver else
                f"Provider {doc.provider.company_name}" if doc.provider else "Fleet Resource"
            )

            provider_users = (
                list(User.objects.filter(role=User.Role.PROVIDER_ADMIN, email=doc.provider.email, is_active=True))
                if (doc.provider and doc.provider.email)
                else []
            )
            for u in provider_users:
                dispatch_notification(
                    user=u,
                    title="⚠️ Document Expiring Soon",
                    message=f"{doc.get_document_type_display()} for {target_name} expires in {days_left} days ({doc.expiry_date}). Upload renewal to prevent lockout.",
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
