import uuid
from django.db import models
from django.conf import settings


class PaymentTransaction(models.Model):
    class PaymentMethod(models.TextChoices):
        CARD = 'CARD', 'Credit / Debit Card'
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Wire Transfer'
        CORPORATE_INVOICE = 'CORPORATE_INVOICE', 'Corporate Credit Account Invoice'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        SUCCESSFUL = 'SUCCESSFUL', 'Payment Successful'
        FAILED = 'FAILED', 'Payment Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    customer_quote = models.ForeignKey(
        'quotations.CustomerQuote',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='GHS')
    payment_method = models.CharField(
        max_length=25,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MOBILE_MONEY
    )
    transaction_reference = models.CharField(
        max_length=100,
        unique=True,
        editable=False
    )
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_made'
    )
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.transaction_reference:
            self.transaction_reference = f"PAY-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.transaction_reference} - {self.currency} {self.amount:,} [{self.get_status_display()}]"


class PaymentReceipt(models.Model):
    transaction = models.OneToOneField(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name='receipt'
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False
    )
    receipt_pdf = models.FileField(upload_to='receipts/%Y/%m/', blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Receipt {self.receipt_number} for {self.transaction.transaction_reference}"


class Invoice(models.Model):
    """Corporate billing invoice for credit/invoice accounts (US-23, US-24, US-101, US-102)."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        PAID = 'PAID', 'Paid'
        OVERDUE = 'OVERDUE', 'Overdue'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(
        'accounts.CorporateCustomer',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    invoice_number = models.CharField(
        max_length=50, unique=True, editable=False
    )
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default='GHS')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    due_date = models.DateField()
    pdf_file = models.FileField(
        upload_to='invoices/%Y/%m/', blank=True, null=True
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.company_name} [{self.get_status_display()}]"


class InvoiceLineItem(models.Model):
    """Individual line items on a consolidated corporate invoice."""

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    request = models.ForeignKey(
        'bookings.TransportationRequest',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_line_items'
    )
    description = models.CharField(max_length=500)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.invoice.currency} {self.amount:,}"


