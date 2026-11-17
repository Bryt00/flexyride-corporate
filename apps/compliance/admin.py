import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from compliance.models import ComplianceDocument, ComplianceAuditLog


@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(ModelAdmin):
    list_display = (
        'document_type', 'target_type', 'get_target_name', 'status_badge',
        'document_number', 'issuing_authority', 'expiry_date', 'verified_by', 'created_at'
    )
    list_filter = ('status', 'target_type', 'document_type')
    search_fields = (
        'document_number', 'issuing_authority', 'provider__company_name',
        'vehicle__registration_number', 'driver__full_name'
    )
    readonly_fields = ('created_at', 'updated_at', 'verified_at')
    raw_id_fields = ('provider', 'vehicle', 'driver', 'verified_by', 'previous_document')
    list_select_related = ('provider', 'vehicle', 'driver', 'verified_by')
    date_hierarchy = 'expiry_date'
    actions = ['mark_as_approved', 'mark_as_rejected', 'mark_as_expiring_soon', 'export_compliance_csv']

    @display(description='Target')
    def get_target_name(self, obj):
        if obj.provider:
            return getattr(obj.provider, 'company_name', 'Provider')
        if obj.vehicle:
            return f"{obj.vehicle.make} {obj.vehicle.model} ({obj.vehicle.registration_number})"
        if obj.driver:
            return getattr(obj.driver, 'full_name', 'Driver')
        return 'Unassigned'

    @display(
        description='Compliance Status',
        label={
            'VERIFIED': 'success',
            'APPROVED': 'success',
            'PENDING_REVIEW': 'info',
            'PENDING': 'info',
            'PENDING_SUBMISSION': 'warning',
            'EXPIRING_SOON': 'warning',
            'EXPIRED': 'danger',
            'REJECTED': 'danger',
            'SUSPENDED': 'danger',
        }
    )
    def status_badge(self, obj):
        return obj.status

    @action(description="Approve & verify selected documents")
    def mark_as_approved(self, request, queryset):
        now = timezone.now()
        for doc in queryset:
            prev = doc.status
            doc.status = ComplianceDocument.Status.VERIFIED
            doc.verified_by = request.user
            doc.verified_at = now
            doc.save()

            if doc.vehicle:
                doc.vehicle.compliance_status = 'VERIFIED'
                doc.vehicle.save(update_fields=['compliance_status'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.APPROVAL,
                actor=request.user,
                document=doc,
                previous_status=prev,
                new_status=ComplianceDocument.Status.VERIFIED,
                notes=f"Admin {request.user.username} approved document in console.",
                request=request
            )
        self.message_user(request, f"Successfully verified {queryset.count()} compliance document(s).")

    @action(description="Reject selected documents")
    def mark_as_rejected(self, request, queryset):
        for doc in queryset:
            prev = doc.status
            doc.status = ComplianceDocument.Status.REJECTED
            doc.verified_by = request.user
            doc.verified_at = timezone.now()
            doc.save()

            if doc.vehicle:
                doc.vehicle.compliance_status = 'REJECTED'
                doc.vehicle.save(update_fields=['compliance_status'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.REJECTION,
                actor=request.user,
                document=doc,
                previous_status=prev,
                new_status=ComplianceDocument.Status.REJECTED,
                notes=f"Admin {request.user.username} rejected document.",
                request=request
            )
        self.message_user(request, f"Rejected {queryset.count()} document(s).")

    @action(description="Mark selected documents as expiring soon")
    def mark_as_expiring_soon(self, request, queryset):
        for doc in queryset:
            prev = doc.status
            doc.status = ComplianceDocument.Status.EXPIRING_SOON
            doc.save(update_fields=['status'])
            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.EXPIRY_DETECTED,
                actor=request.user,
                document=doc,
                previous_status=prev,
                new_status=ComplianceDocument.Status.EXPIRING_SOON,
                notes="Flagged expiring soon.",
                request=request
            )
        self.message_user(request, f"Flagged {queryset.count()} document(s) as expiring soon.")

    @action(description="Export compliance records to CSV")
    def export_compliance_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="compliance_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Doc Type', 'Target Type', 'Target', 'Document Number', 'Authority', 'Status', 'Expiry Date', 'Verified By'])
        for doc in queryset.select_related('provider', 'vehicle', 'driver', 'verified_by'):
            writer.writerow([
                doc.get_document_type_display(),
                doc.get_target_type_display(),
                str(doc.provider or doc.vehicle or doc.driver or 'N/A'),
                doc.document_number or 'N/A',
                doc.issuing_authority or 'N/A',
                doc.get_status_display(),
                doc.expiry_date.strftime("%Y-%m-%d") if doc.expiry_date else 'N/A',
                doc.verified_by.username if doc.verified_by else 'Unverified'
            ])
        return response


@admin.register(ComplianceAuditLog)
class ComplianceAuditLogAdmin(ModelAdmin):
    list_display = (
        'action_badge', 'provider', 'vehicle', 'document',
        'previous_status', 'new_status', 'actor', 'created_at'
    )
    list_filter = ('action', 'created_at')
    search_fields = (
        'provider__company_name', 'vehicle__registration_number',
        'notes', 'actor__username'
    )
    readonly_fields = (
        'action', 'provider', 'vehicle', 'document',
        'previous_status', 'new_status', 'actor', 'notes',
        'ip_address', 'created_at'
    )
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(
        description='Action',
        label={
            'APPROVAL': 'success',
            'PROVIDER_REACTIVATION': 'success',
            'VEHICLE_REACTIVATION': 'success',
            'UPLOAD': 'info',
            'REPLACEMENT': 'info',
            'EXPIRY_DETECTED': 'warning',
            'REJECTION': 'danger',
            'PROVIDER_SUSPENSION': 'danger',
            'VEHICLE_SUSPENSION': 'danger',
            'PAYSTACK_STATUS_CHANGE': 'warning',
        }
    )
    def action_badge(self, obj):
        return obj.action
