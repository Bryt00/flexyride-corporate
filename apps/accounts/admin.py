from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from accounts.models import User, CorporateCustomer, CompanyEmployee, ProviderCompany


# Unregister default Group and re-register with Unfold ModelAdmin
admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('FlexyRide Corporate', {
            'fields': ('role', 'phone_number', 'is_verified'),
        }),
    )


@admin.register(CorporateCustomer)
class CorporateCustomerAdmin(ModelAdmin):
    list_display = ('company_name', 'contact_email', 'status', 'billing_type', 'preferred_currency', 'created_at')
    list_filter = ('status', 'billing_type', 'preferred_currency')
    search_fields = ('company_name', 'registration_number', 'contact_email', 'tax_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('company_name', 'registration_number', 'tax_id', 'contact_email', 'contact_phone', 'address', 'status')
        }),
        ('Billing & Payment Terms', {
            'fields': ('billing_type', 'credit_limit', 'payment_terms_days', 'preferred_currency')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProviderCompany)
class ProviderCompanyAdmin(ModelAdmin):
    list_display = ('company_name', 'contact_person', 'status', 'overall_rating', 'specializations', 'created_at')
    list_filter = ('status',)
    search_fields = ('company_name', 'registration_number', 'contact_person', 'email', 'service_area')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('company_name', 'registration_number', 'contact_person', 'phone', 'email', 'address', 'status', 'overall_rating')
        }),
        ('Capabilities', {
            'fields': ('service_area', 'specializations', 'response_time_avg')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
