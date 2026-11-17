from typing import TYPE_CHECKING
from django.db import models
from django.conf import settings
from django.utils import timezone


class ComplianceDocument(models.Model):
    class TargetType(models.TextChoices):
        PROVIDER = 'PROVIDER', 'Provider Company'
        VEHICLE = 'VEHICLE', 'Vehicle'
        DRIVER = 'DRIVER', 'Driver'

    class DocumentType(models.TextChoices):
        # Provider-level
        OPERATOR_LICENSE = 'OPERATOR_LICENSE', 'Commercial Vehicle Operator Licence'
        BUSINESS_LICENSE = 'BUSINESS_LICENSE', 'Business License / Registration'
        TAX_CERTIFICATE = 'TAX_CERTIFICATE', 'Tax Compliance Certificate'
        # Vehicle-level
        VEHICLE_REGISTRATION = 'VEHICLE_REGISTRATION', 'Vehicle Registration Document'
        ROADWORTHINESS = 'ROADWORTHINESS', 'Roadworthiness Certificate'
        COMMERCIAL_INSURANCE = 'COMMERCIAL_INSURANCE', 'Vehicle Insurance Policy'
        INSURANCE = 'INSURANCE', 'Vehicle Insurance Policy (Legacy)'
        # Driver-level
        DRIVERS_LICENSE = 'DRIVERS_LICENSE', "Driver's License"
        POLICE_CLEARANCE = 'POLICE_CLEARANCE', 'Police Background Check'
        OTHER = 'OTHER', 'Other Operational Document'

    class Status(models.TextChoices):
        PENDING_SUBMISSION = 'PENDING_SUBMISSION', 'Pending Submission'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Review'
        PENDING = 'PENDING', 'Pending Review (Legacy)'
        VERIFIED = 'VERIFIED', 'Verified'
        APPROVED = 'APPROVED', 'Approved (Legacy)'
        REJECTED = 'REJECTED', 'Rejected'
        EXPIRING_SOON = 'EXPIRING_SOON', 'Expiring Soon'
        EXPIRED = 'EXPIRED', 'Expired'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    target_type = models.CharField(
        max_length=20,
        choices=TargetType.choices,
        help_text="Entity type this compliance document belongs to."
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices
    )
    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='compliance_documents',
        null=True,
        blank=True
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle',
        on_delete=models.CASCADE,
        related_name='compliance_documents',
        null=True,
        blank=True
    )
    driver = models.ForeignKey(
        'fleet.Driver',
        on_delete=models.CASCADE,
        related_name='compliance_documents',
        null=True,
        blank=True
    )
    document_file = models.FileField(upload_to='compliance_docs/%Y/%m/')
    document_number = models.CharField(max_length=100, blank=True, null=True)
    issuing_authority = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="e.g. DVLA, National Road Safety Authority (NRSA), Registrar General"
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_REVIEW
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_compliance_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Administrator compliance review notes")
    previous_document = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='renewals',
        help_text="Reference to prior document if this submission is a renewal"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_compliant(self):
        """Returns True if document is verified/approved and not expired."""
        if self.status not in (self.Status.VERIFIED, self.Status.APPROVED, 'VERIFIED', 'APPROVED'):
            return False
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        return True

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    if TYPE_CHECKING:
        def get_document_type_display(self) -> str: ...
        def get_status_display(self) -> str: ...
        def get_target_type_display(self) -> str: ...

    def __str__(self):
        target = self.provider or self.vehicle or self.driver or "Unassigned"
        return f"{self.get_document_type_display()} - {target} [{self.get_status_display()}]"


class ComplianceAuditLog(models.Model):
    class Action(models.TextChoices):
        UPLOAD = 'UPLOAD', 'Document Upload'
        REPLACEMENT = 'REPLACEMENT', 'Document Replacement'
        APPROVAL = 'APPROVAL', 'Document Approved / Verified'
        REJECTION = 'REJECTION', 'Document Rejected'
        EXPIRY_DETECTED = 'EXPIRY_DETECTED', 'Expiry Detected'
        PROVIDER_SUSPENSION = 'PROVIDER_SUSPENSION', 'Provider Suspended'
        PROVIDER_REACTIVATION = 'PROVIDER_REACTIVATION', 'Provider Reactivated'
        VEHICLE_SUSPENSION = 'VEHICLE_SUSPENSION', 'Vehicle Suspended'
        VEHICLE_REACTIVATION = 'VEHICLE_REACTIVATION', 'Vehicle Reactivated'
        PAYSTACK_STATUS_CHANGE = 'PAYSTACK_STATUS_CHANGE', 'Paystack Verification Change'

    provider = models.ForeignKey(
        'accounts.ProviderCompany',
        on_delete=models.CASCADE,
        related_name='compliance_audit_logs',
        null=True,
        blank=True
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle',
        on_delete=models.SET_NULL,
        related_name='compliance_audit_logs',
        null=True,
        blank=True
    )
    document = models.ForeignKey(
        'compliance.ComplianceDocument',
        on_delete=models.SET_NULL,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    action = models.CharField(
        max_length=40,
        choices=Action.choices
    )
    previous_status = models.CharField(max_length=50, blank=True, default='')
    new_status = models.CharField(max_length=50, blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_actions'
    )
    notes = models.TextField(blank=True, default='')
    ip_address = models.CharField(max_length=45, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Compliance Audit Log'
        verbose_name_plural = 'Compliance Audit Logs'

    @classmethod
    def log_action(cls, action, actor=None, provider=None, vehicle=None, document=None,
                   previous_status='', new_status='', notes='', request=None):
        ip = ''
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '')
            if not actor and getattr(request, 'user', None) and request.user.is_authenticated:
                actor = request.user

        prov = provider or (vehicle.provider if vehicle else None) or (document.provider if document else None)
        veh = vehicle or (document.vehicle if document else None)

        return cls.objects.create(
            action=action,
            actor=actor,
            provider=prov,
            vehicle=veh,
            document=document,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
            ip_address=ip[:45]
        )

    def __str__(self):
        return f"{self.get_action_display()} - {self.provider or self.vehicle} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
