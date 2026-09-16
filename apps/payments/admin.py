import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display, action
from payments.models import PaymentTransaction, PaymentReceipt, Invoice, InvoiceLineItem


class PaymentReceiptInline(StackedInline):
    model = PaymentReceipt
    extra = 0
    readonly_fields = ('receipt_number', 'issued_at')


class InvoiceLineItemInline(TabularInline):
    model = InvoiceLineItem
    extra = 0
    fields = ('description', 'request', 'quantity', 'unit_price', 'amount')
    readonly_fields = ('amount', 'created_at')
    raw_id_fields = ('request',)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = (
        'transaction_reference', 'request', 'amount_display',
        'payment_method', 'status_badge', 'payment_date'
    )
    list_filter = ('status', 'payment_method', 'currency')
    search_fields = ('transaction_reference', 'gateway_reference', 'request__request_number')
    readonly_fields = ('transaction_reference', 'created_at')
    raw_id_fields = ('request', 'customer_quote', 'paid_by')
    list_select_related = ('request', 'customer_quote', 'paid_by')
    inlines = [PaymentReceiptInline]
    actions = ['export_transactions_csv']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('amount', 'currency', 'payment_method', 'request', 'customer_quote')
        return self.readonly_fields

    @display(description='Amount')
    def amount_display(self, obj):
        return f"{obj.currency} {obj.amount:,.2f}"

    @display(description='Payment Status')
    def status_badge(self, obj):
        color_map = {
            'SUCCESSFUL': 'green',
            'PENDING': 'amber',
            'FAILED': 'red',
            'REFUNDED': 'red',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )

    @action(description="Export payment transactions to CSV")
    def export_transactions_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="transactions_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Reference', 'Request', 'Amount', 'Currency', 'Method', 'Status', 'Date'])
        for tx in queryset.select_related('request'):
            writer.writerow([
                tx.transaction_reference,
                tx.request.request_number if tx.request else 'N/A',
                tx.amount,
                tx.currency,
                tx.get_payment_method_display(),
                tx.get_status_display(),
                tx.payment_date.strftime("%Y-%m-%d %H:%M") if tx.payment_date else ''
            ])
        return response


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(ModelAdmin):
    list_display = ('receipt_number', 'transaction_ref', 'customer_name', 'amount_display', 'issued_at')
    search_fields = (
        'receipt_number',
        'transaction__transaction_reference',
        'transaction__request__customer__company_name'
    )
    readonly_fields = ('receipt_number', 'issued_at')
    raw_id_fields = ('transaction',)
    list_select_related = ('transaction__request__customer',)

    @display(description='Transaction Reference')
    def transaction_ref(self, obj):
        return obj.transaction.transaction_reference

    @display(description='Corporate Customer')
    def customer_name(self, obj):
        req = getattr(obj.transaction, 'request', None)
        return req.customer.company_name if (req and req.customer) else 'N/A'

    @display(description='Total Paid')
    def amount_display(self, obj):
        return f"{obj.transaction.currency} {obj.transaction.amount:,.2f}"


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = (
        'invoice_number', 'customer', 'total_display',
        'status_badge', 'billing_period_start', 'billing_period_end', 'due_date'
    )
    list_filter = ('status', 'currency')
    search_fields = ('invoice_number', 'customer__company_name')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    raw_id_fields = ('customer',)
    list_select_related = ('customer',)
    date_hierarchy = 'due_date'
    inlines = [InvoiceLineItemInline]
    actions = ['mark_invoices_paid', 'export_invoices_csv']

    @display(description='Total Due')
    def total_display(self, obj):
        return f"{obj.currency} {obj.total:,.2f}"

    @display(description='Invoice Status')
    def status_badge(self, obj):
        color_map = {
            'PAID': 'green',
            'SENT': 'blue',
            'OVERDUE': 'red',
            'DRAFT': 'amber',
            'CANCELLED': 'gray',
        }
        cls = color_map.get(obj.status, 'gray')
        return format_html(
            '<span class="badge-pill badge-pill-{}"><span class="badge-pill-dot"></span>{}</span>',
            cls, obj.get_status_display()
        )

    @action(description="Mark selected invoices as Paid")
    def mark_invoices_paid(self, request, queryset):
        updated = queryset.update(status=Invoice.Status.PAID)
        self.message_user(request, f"Marked {updated} invoice(s) as Paid.")

    @action(description="Export invoices to CSV")
    def export_invoices_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="invoices_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice Number', 'Customer', 'Total', 'Currency', 'Status', 'Due Date'])
        for inv in queryset.select_related('customer'):
            writer.writerow([
                inv.invoice_number,
                inv.customer.company_name,
                inv.total,
                inv.currency,
                inv.get_status_display(),
                inv.due_date.strftime("%Y-%m-%d") if inv.due_date else ''
            ])
        return response
