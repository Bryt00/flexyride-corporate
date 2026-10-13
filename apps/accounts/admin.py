from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from accounts.models import User, BrokerStaff, CorporateCustomer, ProviderCompany


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
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'is_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    actions = ['deactivate_users', 'activate_users']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('FlexyRide Corporate', {
            'fields': ('role', 'phone_number', 'is_verified'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


    @admin.action(description="Restrict / Deactivate selected users")
    def deactivate_users(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} user(s) deactivated and restricted.")

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} user(s) activated.")


@admin.register(BrokerStaff)
class BrokerStaffAdmin(BaseUserAdmin, ModelAdmin):
    """Admin interface for managing and restricting Broker / Customer Representative accounts."""
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_active', 'is_staff', 'is_verified', 'last_login')
    list_filter = ('is_active', 'is_staff', 'is_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    actions = ['deactivate_brokers', 'activate_brokers', 'revoke_staff_access', 'grant_staff_access']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Account Status & Permissions', {
            'fields': ('is_active', 'is_verified', 'is_staff', 'groups', 'user_permissions'),
            'description': 'Toggle "Active" off to immediately restrict and suspend broker portal access.',
        }),
        ('Activity History', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.BROKER)

    def save_model(self, request, obj, form, change):
        if isinstance(obj, User):
            obj.role = User.Role.BROKER
            obj.is_superuser = False
        super().save_model(request, obj, form, change)

    @admin.action(description="Restrict / Deactivate selected broker accounts")
    def deactivate_brokers(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} broker account(s) deactivated and restricted from portal access.")

    @admin.action(description="Activate selected broker accounts")
    def activate_brokers(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} broker account(s) activated.")

    @admin.action(description="Revoke staff portal access")
    def revoke_staff_access(self, request, queryset):
        count = queryset.update(is_staff=False)
        self.message_user(request, f"{count} broker account(s) staff access revoked.")

    @admin.action(description="Grant staff portal access")
    def grant_staff_access(self, request, queryset):
        count = queryset.update(is_staff=True)
        self.message_user(request, f"{count} broker account(s) granted staff access.")


@admin.register(CorporateCustomer)
class CorporateCustomerAdmin(ModelAdmin):
    list_display = ('company_name', 'contact_email', 'contact_phone', 'status', 'billing_type', 'preferred_currency')
    list_filter = ('status', 'billing_type', 'preferred_currency')
    search_fields = ('company_name', 'registration_number', 'contact_email', 'tax_id')
    fieldsets = (
        (None, {
            'fields': ('company_name', 'registration_number', 'tax_id', 'contact_email', 'contact_phone', 'address', 'status')
        }),
        ('Billing & Payment Terms', {
            'fields': ('billing_type', 'credit_limit', 'payment_terms_days', 'preferred_currency')
        }),
    )


class ProviderCompanyAdminForm(forms.ModelForm):
    specializations = forms.MultipleChoiceField(
        required=False,
        label='Specializations / Fleet Categories',
        help_text='Select one or more active fleet categories created by admin.',
        widget=forms.SelectMultiple(attrs={'class': 'w-full'})
    )

    class Meta:
        model = ProviderCompany
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from fleet.models import VehicleCategoryRate
        rates = VehicleCategoryRate.get_cached_active_rates()
        choices = []
        for r in rates:
            choices.append((r.display_name, r.display_name))
        choices.append(('All Fleet Categories', 'All Fleet Categories (Full Service)'))

        initial_vals = []
        if self.instance and self.instance.pk and self.instance.specializations:
            raw = self.instance.specializations
            initial_vals = [s.strip() for s in raw.split(',') if s.strip()]
            for val in initial_vals:
                if val not in [c[0] for c in choices]:
                    choices.append((val, f"{val} (Custom)"))
            self.initial['specializations'] = initial_vals

        specializations_field = self.fields.get('specializations')
        if isinstance(specializations_field, forms.ChoiceField):
            specializations_field.choices = choices

    def clean_specializations(self):
        selected = self.cleaned_data.get('specializations') or []
        if isinstance(selected, (list, tuple)):
            return ", ".join(selected)
        return str(selected)


@admin.register(ProviderCompany)
class ProviderCompanyAdmin(ModelAdmin):
    form = ProviderCompanyAdminForm
    list_display = (
        'company_name', 'contact_person', 'phone', 'email', 'status',
        'payout_channel', 'paystack_subaccount_code', 'overall_rating'
    )
    list_filter = ('status', 'payout_channel', 'specializations')
    search_fields = (
        'company_name', 'registration_number', 'contact_person',
        'email', 'phone', 'account_number', 'paystack_subaccount_code'
    )
    readonly_fields = (
        'paystack_subaccount_code', 'paystack_subaccount_status', 'paystack_subaccount_synced_at'
    )
    fieldsets = (
        (None, {
            'fields': ('company_name', 'registration_number', 'contact_person', 'phone', 'email', 'address', 'status', 'overall_rating')
        }),
        ('Capabilities', {
            'fields': ('service_area', 'specializations', 'response_time_avg')
        }),
        ('Payout & Settlement Banking (Paystack Subaccount)', {
            'fields': (
                'payout_channel', 'settlement_bank', 'settlement_bank_name',
                'account_number', 'account_name', 'percentage_charge',
                'paystack_subaccount_code', 'paystack_subaccount_status', 'paystack_subaccount_synced_at'
            )
        }),
    )
    actions = ['sync_selected_paystack_subaccounts']

    @admin.action(description="Sync Paystack Subaccount for selected providers")
    def sync_selected_paystack_subaccounts(self, request, queryset):
        success_count = 0
        for provider in queryset:
            if provider.has_payout_details:
                res = provider.sync_paystack_subaccount()
                if res.get('success'):
                    success_count += 1
        self.message_user(request, f"Successfully synced Paystack subaccounts for {success_count} provider(s).")

