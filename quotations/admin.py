from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from quotations.models import ProviderQuoteRequest, ProviderQuote, QuoteNegotiation, CustomerQuote, CommissionTier


class ProviderQuoteInline(TabularInline):
    model = ProviderQuote
    extra = 0
    fields = ('provider', 'offered_cost', 'status', 'valid_until', 'submitted_at')
    readonly_fields = ('submitted_at',)


class QuoteNegotiationInline(TabularInline):
    model = QuoteNegotiation
    extra = 0
    readonly_fields = ('timestamp',)


@admin.register(ProviderQuoteRequest)
class ProviderQuoteRequestAdmin(ModelAdmin):
    list_display = ('request', 'provider', 'status_badge', 'requested_at')
    list_filter = ('status',)
    search_fields = ('request__request_number', 'provider__company_name')
    readonly_fields = ('requested_at',)
    raw_id_fields = ('request', 'provider')
    list_select_related = ('request', 'provider')
    inlines = [ProviderQuoteInline]

    @display(description='Status')
    def status_badge(self, obj):
        color_map = {
            'ACCEPTED': 'green',
            'SUBMITTED': 'blue',
            'PENDING': 'amber',
            'DECLINED': 'red',
            'EXPIRED': 'gray',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )


@admin.register(ProviderQuote)
class ProviderQuoteAdmin(ModelAdmin):
    list_display = ('id', 'provider', 'cost_display', 'status_badge', 'valid_until', 'submitted_at')
    list_filter = ('status',)
    search_fields = ('provider__company_name', 'quote_request__request__request_number')
    readonly_fields = ('submitted_at', 'updated_at')
    raw_id_fields = ('quote_request', 'provider', 'proposed_vehicle')
    list_select_related = ('quote_request', 'provider', 'proposed_vehicle')
    inlines = [QuoteNegotiationInline]

    @display(description='Offered Cost')
    def cost_display(self, obj):
        return f"GHS {obj.offered_cost:,.2f}"

    @display(description='Status')
    def status_badge(self, obj):
        color_map = {
            'ACCEPTED': 'green',
            'SUBMITTED': 'blue',
            'REVISED': 'purple',
            'PENDING': 'amber',
            'DECLINED': 'red',
            'EXPIRED': 'gray',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )


@admin.register(CustomerQuote)
class CustomerQuoteAdmin(ModelAdmin):
    list_display = (
        'request', 'customer_price_display', 'provider_cost_display',
        'margin_display', 'status_badge', 'created_at'
    )
    list_filter = ('status',)
    search_fields = ('request__request_number',)
    readonly_fields = ('margin_amount', 'created_at', 'updated_at')
    raw_id_fields = ('request', 'selected_provider_quote', 'created_by')
    list_select_related = ('request', 'selected_provider_quote', 'created_by')
    actions = ['mark_quotes_sent']

    fieldsets = (
        (None, {
            'fields': ('request', 'selected_provider_quote', 'status', 'created_by')
        }),
        ('Pricing (Commercial Confidential)', {
            'fields': ('provider_cost', 'margin_amount', 'final_customer_price'),
            'description': '⚠️ Provider cost and margin are hidden from non-broker roles (US-49, US-108).'
        }),
        ('Customer Response', {
            'fields': ('sent_at', 'customer_decision_at', 'customer_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def _can_view_margins(self, user):
        return user.is_superuser or getattr(user, 'role', None) in ['SYSTEM_ADMIN', 'BROKER']

    def get_list_display(self, request):
        if not self._can_view_margins(request.user):
            return ('request', 'customer_price_display', 'status_badge', 'created_at')
        return self.list_display

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if not self._can_view_margins(request.user):
            return [
                (title, opts) if title != 'Pricing (Commercial Confidential)'
                else ('Pricing', {'fields': ('final_customer_price',)})
                for title, opts in fieldsets
            ]
        return fieldsets

    @display(description='Customer Price')
    def customer_price_display(self, obj):
        return f"GHS {obj.final_customer_price:,.2f}"

    @display(description='Provider Cost')
    def provider_cost_display(self, obj):
        return f"GHS {obj.provider_cost:,.2f}"

    @display(description='Margin')
    def margin_display(self, obj):
        return f"GHS {obj.margin_amount:,.2f}"

    @display(description='Quote Status')
    def status_badge(self, obj):
        color_map = {
            'ACCEPTED': 'green',
            'SENT': 'blue',
            'CHANGE_REQUESTED': 'purple',
            'DRAFT': 'amber',
            'DECLINED': 'red',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )

    @action(description="Mark selected quotes as Sent to Customer")
    def mark_quotes_sent(self, request, queryset):
        updated = queryset.update(status=CustomerQuote.Status.SENT, sent_at=timezone.now())
        self.message_user(request, f"Updated {updated} quote(s) to Sent status.")


@admin.register(QuoteNegotiation)
class QuoteNegotiationAdmin(ModelAdmin):
    list_display = ('id', 'provider_quote', 'broker', 'counter_cost_display', 'timestamp')
    search_fields = ('provider_quote__provider__company_name', 'broker__username', 'notes')
    readonly_fields = ('timestamp',)
    raw_id_fields = ('provider_quote', 'broker')
    list_select_related = ('provider_quote__provider', 'broker')

    @display(description='Proposed Counter Cost')
    def counter_cost_display(self, obj):
        return f"GHS {obj.proposed_counter_cost:,.2f}"


@admin.register(CommissionTier)
class CommissionTierAdmin(ModelAdmin):
    list_display = (
        'name', 'vehicle_category', 'distance_range', 'margin_percentage',
        'min_margin_amount', 'auto_dispatch_quote', 'is_active', 'priority'
    )
    list_editable = ('margin_percentage', 'min_margin_amount', 'auto_dispatch_quote', 'is_active', 'priority')
    list_filter = ('is_active', 'auto_dispatch_quote', 'vehicle_category')
    search_fields = ('name',)
    ordering = ('-priority', 'name')

    @display(description='Distance Range')
    def distance_range(self, obj):
        if obj.max_distance_km:
            return f"{obj.min_distance_km} - {obj.max_distance_km} km"
        return f">= {obj.min_distance_km} km"
