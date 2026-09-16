from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from fleet.models import Vehicle, VehiclePhoto, Driver, VehicleCategoryRate


class VehiclePhotoInline(TabularInline):
    model = VehiclePhoto
    extra = 0
    fields = ('image', 'is_primary', 'caption')


@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin):
    list_display = (
        'registration_number', 'make', 'model', 'category', 'provider',
        'status_badge', 'compliance_badge', 'seating_capacity'
    )
    list_filter = ('category', 'status', 'compliance_status', 'has_accessibility', 'wifi_available')
    search_fields = ('registration_number', 'make', 'model', 'provider__company_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('provider',)
    list_select_related = ('provider',)
    inlines = [VehiclePhotoInline]
    actions = ['mark_as_available', 'mark_as_maintenance']

    @display(description='Fleet Status')
    def status_badge(self, obj):
        color_map = {
            'AVAILABLE': 'green',
            'ASSIGNED': 'blue',
            'MAINTENANCE': 'amber',
            'INACTIVE': 'red',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )

    @display(description='Compliance')
    def compliance_badge(self, obj):
        color_map = {
            'COMPLIANT': 'green',
            'PENDING_REVIEW': 'amber',
            'NON_COMPLIANT': 'red',
        }
        cls = color_map.get(obj.compliance_status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_compliance_status_display()
        )

    @action(description="Mark selected vehicles as Available")
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status=Vehicle.Status.AVAILABLE)
        self.message_user(request, f"Marked {updated} vehicle(s) as Available.")

    @action(description="Mark selected vehicles as In Maintenance")
    def mark_as_maintenance(self, request, queryset):
        updated = queryset.update(status=Vehicle.Status.MAINTENANCE)
        self.message_user(request, f"Marked {updated} vehicle(s) as In Maintenance.")


@admin.register(Driver)
class DriverAdmin(ModelAdmin):
    list_display = (
        'full_name', 'provider', 'phone_number', 'status_badge',
        'compliance_badge', 'rating_badge', 'license_expiry'
    )
    list_filter = ('status', 'compliance_status', 'provider')
    search_fields = ('full_name', 'phone_number', 'license_number', 'provider__company_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('provider', 'user')
    list_select_related = ('provider', 'user')
    actions = ['mark_as_available', 'mark_as_off_duty']

    @display(description='Status')
    def status_badge(self, obj):
        color_map = {
            'AVAILABLE': 'green',
            'ON_TRIP': 'blue',
            'OFF_DUTY': 'amber',
            'INACTIVE': 'red',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )

    @display(description='Compliance')
    def compliance_badge(self, obj):
        color_map = {
            'COMPLIANT': 'green',
            'PENDING_REVIEW': 'amber',
            'NON_COMPLIANT': 'red',
        }
        cls = color_map.get(obj.compliance_status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_compliance_status_display()
        )

    @display(description='Rating')
    def rating_badge(self, obj):
        rating_val = float(obj.rating or 0.0)
        return format_html(
            '<span class="badge-pill badge-pill-green" style="font-weight:700;">★ {}</span>',
            f"{rating_val:.1f}"
        )

    @action(description="Mark selected drivers as Available")
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status=Driver.Status.AVAILABLE)
        self.message_user(request, f"Marked {updated} driver(s) as Available.")

    @action(description="Mark selected drivers as Off Duty")
    def mark_as_off_duty(self, request, queryset):
        updated = queryset.update(status=Driver.Status.OFF_DUTY)
        self.message_user(request, f"Marked {updated} driver(s) as Off Duty.")


@admin.register(VehicleCategoryRate)
class VehicleCategoryRateAdmin(ModelAdmin):
    list_display = (
        'category', 'display_name', 'base_wholesale_rate', 'per_km_rate',
        'daily_charter_rate', 'min_seating_capacity', 'recommended_models',
        'is_active', 'display_order'
    )
    list_editable = ('base_wholesale_rate', 'per_km_rate', 'daily_charter_rate', 'is_active', 'display_order')
    list_filter = ('is_active', 'category')
    search_fields = ('display_name', 'recommended_models', 'description')
    ordering = ('display_order', 'category')
