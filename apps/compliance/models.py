from django.db import models
from django.conf import settings
from django.utils import timezone


class ComplianceDocument(models.Model):
    class TargetType(models.TextChoices):
        PROVIDER = 'PROVIDER', 'Provider Company'
        VEHICLE = 'VEHICLE', 'Vehicle'
        DRIVER = 'DRIVER', 'Driver'

    class DocumentType(models.TextChoices):
        BUSINESS_LICENSE = 'BUSINESS_LICENSE', 'Business License / Registration'
        TAX_CERTIFICATE = 'TAX_CERTIFICATE', 'Tax Compliance Certificate'
        INSURANCE = 'INSURANCE', 'Vehicle Insurance Policy'
        ROADWORTHINESS = 'ROADWORTHINESS', 'Roadworthiness Certificate'
        DRIVERS_LICENSE = 'DRIVERS_LICENSE', 'Driver\'s License'
        POLICE_CLEARANCE = 'POLICE_CLEARANCE', 'Police Background Check'
        OTHER = 'OTHER', 'Other Operational Document'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        EXPIRING_SOON = 'EXPIRING_SOON', 'Expiring Soon'
        EXPIRED = 'EXPIRED', 'Expired'
        REJECTED = 'REJECTED', 'Rejected'

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
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_compliant(self):
        """Returns True if document is approved and not expired."""
        if self.status != self.Status.APPROVED:
            return False
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        return True

    def __str__(self):
        target = self.provider or self.vehicle or self.driver or "Unassigned"
        return f"{self.get_document_type_display()} - {target} [{self.get_status_display()}]"

