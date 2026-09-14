import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from bookings.models import (
    TransportationRequest, PassengerInfo, VehicleAssignment,
    RecurringSchedule, CancellationRequest
)


class PassengerInfoInline(TabularInline):
    model = PassengerInfo
    extra = 0
    fields = ('full_name', 'phone_number', 'email', 'is_primary', 'tracking_token')
    readonly_fields = ('tracking_token',)


class VehicleAssignmentInline(TabularInline):
    model = VehicleAssignment
    extra = 0
    fields = ('vehicle', 'driver', 'status', 'assigned_at', 'replacement_reason')
    readonly_fields = ('assigned_at',)
    raw_id_fields = ('vehicle', 'driver')


class RecurringScheduleInline(TabularInline):
    model = RecurringSchedule
    extra = 0


class CancellationRequestInline(TabularInline):
    model = CancellationRequest
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(TransportationRequest)
class TransportationRequestAdmin(ModelAdmin):
    list_display = (
        'request_number', 'customer', 'journey_type', 'status_badge',
        'priority_badge', 'departure_datetime', 'assigned_broker', 'portal_link', 'created_at'
    )
    list_filter = (
        'booking_status', 'journey_type', 'priority_level',
        'internal_approval_status', 'requested_vehicle_category'
    )
    search_fields = (
        'request_number', 'customer__company_name', 'requester__username',
        'pickup_address', 'destination_address', 'customer_reference', 'flight_number'
    )
    readonly_fields = ('request_number', 'portal_direct_button', 'created_at', 'updated_at')
    raw_id_fields = ('customer', 'requester', 'approved_by', 'assigned_broker')
    list_select_related = ('customer', 'requester', 'assigned_broker')
    date_hierarchy = 'departure_datetime'
    inlines = [PassengerInfoInline, VehicleAssignmentInline, RecurringScheduleInline, CancellationRequestInline]
    actions = ['approve_selected_requests', 'export_bookings_to_csv']
    
    fieldsets = (
        ('Request Info', {
            'fields': ('request_number', 'portal_direct_button', 'customer', 'requester', 'journey_type', 'priority_level', 'customer_reference')
        }),
        ('Internal Approval', {
            'fields': ('internal_approval_status', 'approved_by', 'approved_at', 'internal_rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Locations', {
            'fields': ('pickup_address', 'pickup_latitude', 'pickup_longitude',
                       'destination_address', 'destination_latitude', 'destination_longitude')
        }),
        ('Schedule', {
            'fields': ('departure_datetime', 'return_datetime', 'duration_hours')
        }),
        ('Flight Details', {
            'fields': ('flight_number', 'airline', 'flight_datetime', 'airport_name'),
            'classes': ('collapse',)
        }),
        ('Vehicle & Requirements', {
            'fields': ('requested_vehicle_category', 'vehicles_requested_count', 'passenger_count',
                       'luggage_requirements', 'accessibility_required', 'child_seats_count',
                       'executive_vehicle_required', 'additional_stops_notes', 'estimated_distance_km')
        }),
        ('Lifecycle', {
            'fields': ('booking_status', 'assigned_broker', 'cancellation_policy_tier')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        status = obj.booking_status
        if status in ['CONFIRMED', 'COMPLETED']:
            cls = 'green'
        elif status in ['ASSIGNED', 'DRIVER_EN_ROUTE', 'DRIVER_ARRIVED', 'PASSENGER_ONBOARD', 'TRIP_IN_PROGRESS']:
            cls = 'blue'
        elif status in ['AWAITING_INTERNAL_APPROVAL', 'BEING_ARRANGED', 'QUOTE_AVAILABLE', 'AWAITING_CUSTOMER_ACCEPTANCE', 'APPROVED_BY_COMPANY']:
            cls = 'amber'
        elif status in ['CANCELLED', 'REJECTED_BY_COMPANY']:
            cls = 'red'
        else:
            cls = 'gray'

        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_booking_status_display()
        )

    @admin.display(description='Priority')
    def priority_badge(self, obj):
        prio = obj.priority_level
        if prio == 'URGENT':
            cls = 'red'
        elif prio == 'STANDARD':
            cls = 'blue'
        else:
            cls = 'gray'

        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_priority_level_display()
        )

    @admin.display(description='Portal View')
    def portal_link(self, obj):
        url = f"/portal/requests/{obj.request_number}/details/"
        return format_html(
            '<a href="{}" target="_blank" class="badge-action-link" title="Open in Portal">'
            '<i data-lucide="external-link" style="width:12px;height:12px;"></i> View'
            '</a>',
            url
        )

    @admin.display(description='Portal Workspace')
    def portal_direct_button(self, obj):
        if not obj.pk:
            return '-'
        url = f"/portal/requests/{obj.request_number}/details/"
        return format_html(
            '<a href="{}" target="_blank" class="badge-action-link" style="display:inline-flex;padding:0.4rem 0.8rem;gap:0.4rem;">'
            '<i data-lucide="external-link" style="width:14px;height:14px;"></i> Open this Booking in Broker Portal'
            '</a>',
            url
        )

    @admin.action(description="Approve selected transportation requests")
    def approve_selected_requests(self, request, queryset):
        updated = queryset.update(
            internal_approval_status=TransportationRequest.InternalApprovalStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f"Successfully approved {updated} booking request(s).")

    @admin.action(description="Export selected bookings to CSV")
    def export_bookings_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="bookings_export_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Request Number', 'Customer', 'Journey Type', 'Status', 'Priority', 'Departure', 'Pickup', 'Destination', 'Passengers'])
        for b in queryset.select_related('customer'):
            writer.writerow([
                b.request_number,
                b.customer.company_name if b.customer else 'N/A',
                b.get_journey_type_display(),
                b.get_booking_status_display(),
                b.get_priority_level_display(),
                b.departure_datetime.strftime("%Y-%m-%d %H:%M") if b.departure_datetime else '',
                b.pickup_address,
                b.destination_address,
                b.passenger_count
            ])
        return response


@admin.register(VehicleAssignment)
class VehicleAssignmentAdmin(ModelAdmin):
    list_display = ('id', 'request_link', 'vehicle', 'driver', 'status_badge', 'assigned_at', 'replacement_reason')
    list_filter = ('status', 'assigned_at')
    search_fields = ('request__request_number', 'vehicle__registration_number', 'driver__full_name')
    readonly_fields = ('assigned_at',)
    raw_id_fields = ('request', 'vehicle', 'driver')
    list_select_related = ('request', 'vehicle', 'driver')
    actions = ['export_assignments_to_csv']

    @admin.display(description='Booking Request')
    def request_link(self, obj):
        return obj.request.request_number

    @admin.display(description='Dispatch Status')
    def status_badge(self, obj):
        color_map = {
            'ASSIGNED': 'blue',
            'EN_ROUTE': 'blue',
            'ARRIVED': 'purple',
            'PASSENGER_ONBOARD': 'purple',
            'TRIP_IN_PROGRESS': 'green',
            'COMPLETED': 'green',
            'CANCELLED': 'red',
            'REPLACED': 'amber',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )

    @admin.action(description="Export assignments to CSV")
    def export_assignments_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="dispatches_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Assignment ID', 'Request', 'Vehicle', 'Driver', 'Status', 'Assigned At', 'Replacement Reason'])
        for a in queryset.select_related('request', 'vehicle', 'driver'):
            writer.writerow([
                a.id,
                a.request.request_number,
                str(a.vehicle),
                str(a.driver),
                a.get_status_display(),
                a.assigned_at.strftime("%Y-%m-%d %H:%M") if a.assigned_at else '',
                a.replacement_reason or ''
            ])
        return response


@admin.register(CancellationRequest)
class CancellationRequestAdmin(ModelAdmin):
    list_display = ('request', 'cancelled_by', 'status_badge', 'cancellation_fee', 'fee_waived', 'refund_amount', 'created_at')
    list_filter = ('status', 'fee_waived')
    search_fields = ('request__request_number', 'reason')
    readonly_fields = ('created_at',)
    raw_id_fields = ('request', 'cancelled_by')
    list_select_related = ('request', 'cancelled_by')

    @admin.display(description='Status')
    def status_badge(self, obj):
        cls = 'red' if obj.status == 'CANCELLED' else 'amber'
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )
