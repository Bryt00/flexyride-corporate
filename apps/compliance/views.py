"""
Compliance and regulatory verification views for FlexyRide Corporate.
Implements the Paystack Compliance & Provider Verification Dashboard (Sections 2, 7, 8, 9, 10, 11, 14).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden, FileResponse, Http404
from django.utils import timezone
from django.db.models import Q

from accounts.models import ProviderCompany
from fleet.models import Vehicle
from bookings.models import VehicleAssignment
from compliance.models import ComplianceDocument, ComplianceAuditLog
from compliance.reports import generate_compliance_report_pdf
from portal.selectors import get_provider_context, get_broker_context
from portal.services import handle_provider_post
from portal.views.base import is_provider, is_broker


def compliance_safety_view(request):
    """Public Compliance & Safety Standards Overview."""
    context = {
        'hide_sidebar': True,
        'hide_navbar': True,
        'active_nav': 'compliance',
        'user_is_auth': request.user.is_authenticated,
        'user_role': getattr(request.user, 'role', None) if request.user.is_authenticated else None,
    }
    return render(request, 'compliance/compliance_safety.html', context)


@login_required
@user_passes_test(is_provider)
def provider_compliance_view(request):
    """Provider Dashboard Compliance Vault."""
    if request.method == 'POST':
        return handle_provider_post(request)
    ctx = get_provider_context(request)
    ctx['active_tab'] = 'provider_compliance'
    company = ctx.get('company')
    if company:
        veh_qs = company.vehicles.all()
        ctx['compliant_vehicles_count'] = veh_qs.filter(compliance_status__in=['VERIFIED', 'COMPLIANT']).count()
        ctx['non_compliant_vehicles_count'] = veh_qs.exclude(compliance_status__in=['VERIFIED', 'COMPLIANT']).count()
    return render(request, 'compliance/provider_compliance.html', ctx)


@login_required
@user_passes_test(is_broker)
def broker_compliance_dashboard_view(request):
    """
    Super Admin / Broker Provider Compliance Management Dashboard (Sections 2 & 9).
    Monitors all transport providers, vehicle compliance matrix, expiry countdowns,
    audit trails, and verification actions.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        redirect_target = request.META.get('HTTP_REFERER') or 'portal_broker_compliance'

        if action == 'approve_document':
            doc_id = request.POST.get('document_id')
            doc = get_object_or_404(ComplianceDocument, id=doc_id)
            prev_status = doc.status
            notes = request.POST.get('notes', '').strip()

            doc.status = ComplianceDocument.Status.VERIFIED
            doc.verified_by = request.user
            doc.verified_at = timezone.now()
            if notes:
                doc.notes = notes
            doc.save()

            # Update vehicle status if both registration and roadworthiness are verified
            if doc.vehicle:
                v = doc.vehicle
                reg_doc = v.registration_document
                rw_doc = v.roadworthiness_document
                if reg_doc and rw_doc and reg_doc.is_compliant() and rw_doc.is_compliant():
                    v.compliance_status = Vehicle.ComplianceStatus.VERIFIED
                    v.save(update_fields=['compliance_status'])
                else:
                    v.compliance_status = Vehicle.ComplianceStatus.PENDING_REVIEW
                    v.save(update_fields=['compliance_status'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.APPROVAL,
                actor=request.user,
                provider=doc.provider,
                vehicle=doc.vehicle,
                document=doc,
                previous_status=prev_status,
                new_status=ComplianceDocument.Status.VERIFIED,
                notes=notes or f"Verified by Compliance Officer {request.user.username}.",
                request=request
            )
            messages.success(request, f"Document #{doc.document_number} approved and marked VERIFIED!")
            return redirect(redirect_target)

        elif action == 'reject_document':
            doc_id = request.POST.get('document_id')
            doc = get_object_or_404(ComplianceDocument, id=doc_id)
            prev_status = doc.status
            reason = request.POST.get('rejection_reason', 'Document failed compliance verification requirements.').strip()

            doc.status = ComplianceDocument.Status.REJECTED
            doc.rejection_reason = reason
            doc.verified_by = request.user
            doc.verified_at = timezone.now()
            doc.save()

            if doc.vehicle:
                doc.vehicle.compliance_status = Vehicle.ComplianceStatus.REJECTED
                doc.vehicle.save(update_fields=['compliance_status'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.REJECTION,
                actor=request.user,
                provider=doc.provider,
                vehicle=doc.vehicle,
                document=doc,
                previous_status=prev_status,
                new_status=ComplianceDocument.Status.REJECTED,
                notes=f"Rejected: {reason}",
                request=request
            )
            messages.warning(request, f"Document #{doc.document_number} rejected. Reason: {reason}")
            return redirect(redirect_target)

        elif action == 'suspend_provider':
            provider_id = request.POST.get('provider_id')
            provider = get_object_or_404(ProviderCompany, id=provider_id)
            reason = request.POST.get('reason', 'Administrative compliance suspension.').strip()
            prev_status = provider.status

            provider.status = ProviderCompany.Status.SUSPENDED
            provider.save(update_fields=['status', 'updated_at'])

            # Block all vehicles
            provider.vehicles.update(compliance_status='SUSPENDED')

            # Flag existing active assignments for review
            active_assignments = VehicleAssignment.objects.filter(
                vehicle__provider=provider,
                status__in=['ASSIGNED', 'EN_ROUTE', 'ARRIVED']
            ).select_related('request')
            for assign in active_assignments:
                flag = f"[SUSPENSION REVIEW] Provider '{provider.company_name}' suspended ({reason}). Review dispatch immediately."
                assign.notes = (assign.notes + f"\n{flag}") if assign.notes else flag
                assign.save(update_fields=['notes'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.PROVIDER_SUSPENSION,
                actor=request.user,
                provider=provider,
                previous_status=prev_status,
                new_status=ProviderCompany.Status.SUSPENDED,
                notes=f"Provider suspended: {reason}",
                request=request
            )
            messages.error(request, f"Provider '{provider.company_name}' suspended from all bookings. Reason: {reason}")
            return redirect(redirect_target)

        elif action == 'reactivate_provider':
            provider_id = request.POST.get('provider_id')
            provider = get_object_or_404(ProviderCompany, id=provider_id)
            prev_status = provider.status

            # Check operating licence validity before clearing suspension
            op_lic = provider.operator_license
            if not op_lic:
                messages.error(request, f"Cannot reactivate '{provider.company_name}': Missing Commercial Vehicle Operator Licence.")
                return redirect(redirect_target)
            if op_lic.is_expired:
                messages.error(request, f"Cannot reactivate '{provider.company_name}': Operator Licence expired on {op_lic.expiry_date}. Valid renewed licence must be approved first.")
                return redirect(redirect_target)
            if op_lic.status not in ('VERIFIED', 'APPROVED'):
                messages.error(request, f"Cannot reactivate '{provider.company_name}': Operator Licence is {op_lic.get_status_display()} (Admin approval required).")
                return redirect(redirect_target)

            provider.status = ProviderCompany.Status.APPROVED
            provider.save(update_fields=['status', 'updated_at'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.PROVIDER_REACTIVATION,
                actor=request.user,
                provider=provider,
                previous_status=prev_status,
                new_status=ProviderCompany.Status.APPROVED,
                notes="Administrative suspension cleared following compliance review.",
                request=request
            )
            messages.success(request, f"Provider '{provider.company_name}' reactivated and cleared for bookings.")
            return redirect(redirect_target)

        elif action == 'suspend_vehicle':
            vehicle_id = request.POST.get('vehicle_id')
            veh = get_object_or_404(Vehicle, id=vehicle_id)
            prev_status = veh.compliance_status
            reason = request.POST.get('reason', 'Suspended by compliance officer.').strip()

            veh.compliance_status = Vehicle.ComplianceStatus.SUSPENDED
            veh.save(update_fields=['compliance_status'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.VEHICLE_SUSPENSION,
                actor=request.user,
                provider=veh.provider,
                vehicle=veh,
                previous_status=prev_status,
                new_status=Vehicle.ComplianceStatus.SUSPENDED,
                notes=f"Vehicle suspended: {reason}",
                request=request
            )
            messages.warning(request, f"Vehicle {veh.registration_number} suspended from dispatch assignments.")
            return redirect(redirect_target)

        elif action == 'reactivate_vehicle':
            vehicle_id = request.POST.get('vehicle_id')
            veh = get_object_or_404(Vehicle, id=vehicle_id)
            prev_status = veh.compliance_status

            ok, reason = veh.is_eligible_for_booking()
            if not ok:
                messages.error(request, f"Cannot reactivate vehicle {veh.registration_number}: {reason}")
                return redirect(redirect_target)

            veh.compliance_status = Vehicle.ComplianceStatus.VERIFIED
            veh.save(update_fields=['compliance_status'])

            ComplianceAuditLog.log_action(
                action=ComplianceAuditLog.Action.VEHICLE_REACTIVATION,
                actor=request.user,
                provider=veh.provider,
                vehicle=veh,
                previous_status=prev_status,
                new_status=Vehicle.ComplianceStatus.VERIFIED,
                notes="Vehicle suspension cleared following compliance audit.",
                request=request
            )
            messages.success(request, f"Vehicle {veh.registration_number} verified and cleared for dispatch.")
            return redirect(redirect_target)

        return redirect(redirect_target)

    # GET Request
    context = get_broker_context(request)
    context['active_tab'] = 'broker_compliance'

    today = timezone.now().date()
    in_30_days = today + timezone.timedelta(days=30)

    # All Providers with prefetches
    all_providers = (
        ProviderCompany.objects.all()
        .prefetch_related('vehicles__compliance_documents', 'compliance_documents__verified_by')
        .order_by('company_name')
    )

    # Compute Super Admin Metrics (Section 9)
    total_providers = all_providers.count()
    verified_providers = sum(1 for p in all_providers if p.compliance_status == 'VERIFIED')
    pending_providers = sum(1 for p in all_providers if p.compliance_status == 'PENDING_REVIEW' or p.compliance_status == 'PENDING_SUBMISSION')
    suspended_providers = sum(1 for p in all_providers if p.compliance_status == 'SUSPENDED')
    expired_providers = sum(1 for p in all_providers if p.compliance_status == 'EXPIRED')

    all_vehicles = Vehicle.objects.all()
    total_vehicles = all_vehicles.count()
    verified_vehicles = all_vehicles.filter(compliance_status__in=['VERIFIED', 'COMPLIANT']).count()
    non_compliant_vehicles = total_vehicles - verified_vehicles

    expiring_soon_docs = ComplianceDocument.objects.filter(
        expiry_date__gt=today,
        expiry_date__lte=in_30_days
    ).count()

    incomplete_paystack = all_providers.filter(
        Q(paystack_subaccount_code__isnull=True) |
        Q(paystack_subaccount_code='') |
        Q(paystack_subaccount_status__istartswith='error')
    ).count()

    # Filtering
    status_filter = request.GET.get('status', 'ALL').upper()
    search_query = request.GET.get('q', '').strip()
    active_sub_tab = request.GET.get('tab', 'providers')

    filtered_providers = list(all_providers)
    if status_filter != 'ALL':
        filtered_providers = [p for p in filtered_providers if p.compliance_status == status_filter]

    if search_query:
        q_lower = search_query.lower()
        filtered_providers = [
            p for p in filtered_providers if
            q_lower in p.company_name.lower() or
            (p.registration_number and q_lower in p.registration_number.lower()) or
            (p.contact_person and q_lower in p.contact_person.lower()) or
            (p.email and q_lower in p.email.lower()) or
            (p.phone and q_lower in p.phone.lower())
        ]

    # Audit Trail Logs
    audit_logs = (
        ComplianceAuditLog.objects.all()
        .select_related('provider', 'vehicle', 'document', 'actor')
        .order_by('-created_at')[:100]
    )

    context.update({
        'total_providers_count': total_providers,
        'verified_providers_count': verified_providers,
        'pending_providers_count': pending_providers,
        'suspended_providers_count': suspended_providers,
        'expired_providers_count': expired_providers,
        'total_vehicles_count': total_vehicles,
        'verified_vehicles_count': verified_vehicles,
        'non_compliant_vehicles_count': non_compliant_vehicles,
        'expiring_soon_count': expiring_soon_docs,
        'incomplete_paystack_count': incomplete_paystack,
        'providers': filtered_providers,
        'audit_logs': audit_logs,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_sub_tab': active_sub_tab,
    })

    return render(request, 'compliance/broker_compliance_dashboard.html', context)


@login_required
@user_passes_test(is_broker)
def compliance_export_report_view(request, provider_id):
    """
    Generates and downloads a Paystack Compliance Evidence Report PDF (Section 11).
    Supports ?redact=1 parameter to redact sensitive PII before export.
    """
    provider = get_object_or_404(ProviderCompany, id=provider_id)
    redact = request.GET.get('redact') == '1'

    buffer = generate_compliance_report_pdf(provider, redact=redact)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Paystack_Compliance_Evidence_FRC_PROV_{provider.id:04d}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def compliance_download_document_view(request, doc_id):
    """
    Secure document download endpoint (Section 14: Security and Private Storage).
    Enforces role-based permissions: only Super Admins, Brokers, or the document's
    owning provider may view or download the file.
    """
    doc = get_object_or_404(ComplianceDocument, id=doc_id)

    # Permission check
    can_access = False
    if is_broker(request.user):
        can_access = True
    elif is_provider(request.user):
        provider = ProviderCompany.objects.filter(
            Q(email=request.user.email) | Q(users=request.user)
        ).first()
        if provider and doc.provider_id == provider.id:
            can_access = True

    if not can_access:
        return HttpResponseForbidden("You do not have permission to access this compliance document.")

    if not doc.document_file:
        raise Http404("Document file not attached.")

    try:
        response = FileResponse(doc.document_file.open('rb'))
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    except Exception:
        raise Http404("File could not be loaded from storage.")
