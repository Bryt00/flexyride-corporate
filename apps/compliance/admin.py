import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from compliance.models import ComplianceDocument


@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(ModelAdmin):
    list_display = (
        'document_type', 'target_type', 'get_target_name', 'status_badge',
        'document_number', 'expiry_date', 'verified_by', 'created_at'
    )
    list_filter = ('status', 'target_type', 'document_type')
    search_fields = (
        'document_number', 'provider__company_name',
        'vehicle__registration_number', 'driver__full_name'
    )
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('provider', 'vehicle', 'driver', 'verified_by')
    list_select_related = ('provider', 'vehicle', 'driver', 'verified_by')
    date_hierarchy = 'expiry_date'
    actions = ['mark_as_approved', 'mark_as_expiring_soon', 'export_compliance_csv']

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
            'APPROVED': 'success',
            'PENDING': 'info',
            'EXPIRING_SOON': 'warning',
            'EXPIRED': 'danger',
            'REJECTED': 'danger',
        }
    )
    def status_badge(self, obj):
        return obj.status

    @action(description="Approve & verify selected documents")
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(
            status=ComplianceDocument.Status.APPROVED,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f"Successfully approved {updated} compliance document(s).")

    @action(description="Mark selected documents as expiring soon")
    def mark_as_expiring_soon(self, request, queryset):
        updated = queryset.update(status=ComplianceDocument.Status.EXPIRING_SOON)
        self.message_user(request, f"Flagged {updated} document(s) as expiring soon.")

    @action(description="Export compliance records to CSV")
    def export_compliance_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="compliance_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Doc Type', 'Target Type', 'Target', 'Document Number', 'Status', 'Expiry Date', 'Verified By'])
        for doc in queryset.select_related('provider', 'vehicle', 'driver', 'verified_by'):
            writer.writerow([
                doc.get_document_type_display(),
                doc.get_target_type_display(),
                str(doc.provider or doc.vehicle or doc.driver or 'N/A'),
                doc.document_number or 'N/A',
                doc.get_status_display(),
                doc.expiry_date.strftime("%Y-%m-%d") if doc.expiry_date else 'N/A',
                doc.verified_by.username if doc.verified_by else 'Unverified'
            ])
        return response
