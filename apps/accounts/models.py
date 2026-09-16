from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Corporate Customer'
        EMPLOYEE_REQUESTER = 'EMPLOYEE_REQUESTER', 'Employee / Requester'
        BROKER = 'BROKER', 'FlexyRide Broker / Staff'
        PROVIDER_ADMIN = 'PROVIDER_ADMIN', 'Provider Administrator'
        DRIVER = 'DRIVER', 'Driver'
        SYSTEM_ADMIN = 'SYSTEM_ADMIN', 'System Administrator'

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.CUSTOMER,
        help_text="Primary functional role of the user within FlexyRide Corporate."
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superuser or self.role in [self.Role.SYSTEM_ADMIN, self.Role.BROKER]:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if not self.is_active:
            return False
        if self.is_superuser or self.role in [self.Role.SYSTEM_ADMIN, self.Role.BROKER]:
            return True
        return super().has_module_perms(app_label)

    def save(self, *args, **kwargs):
        if self.role in [self.Role.SYSTEM_ADMIN, self.Role.BROKER]:
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class CorporateCustomer(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    class BillingType(models.TextChoices):
        PREPAID = 'PREPAID', 'Prepaid'
        CREDIT = 'CREDIT', 'Credit Account'
        INVOICE = 'INVOICE', 'Monthly Invoice'

    company_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    logo = models.ImageField(
        upload_to='company_logos/%Y/%m/',
        null=True,
        blank=True,
        help_text="Corporate company brand logo."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    # Billing & Payment Terms (US-23, US-24)
    billing_type = models.CharField(
        max_length=20,
        choices=BillingType.choices,
        default=BillingType.PREPAID,
        help_text="How this customer is billed."
    )
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Maximum outstanding credit balance allowed."
    )
    payment_terms_days = models.PositiveIntegerField(
        default=30,
        help_text="Net payment terms in days (e.g. 30, 60, 90)."
    )
    preferred_currency = models.CharField(
        max_length=10, default='GHS',
        help_text="Preferred billing currency."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.company_name} [{self.get_status_display()}]"


class CompanyEmployee(models.Model):
    company = models.ForeignKey(
        CorporateCustomer,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    can_approve_requests = models.BooleanField(
        default=False,
        help_text="Determines if this employee can approve transportation requests internally."
    )
    spending_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional max budget allowance per journey."
    )
    # Organisational structure (US-03, US-08)
    department = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Employee's department within the company."
    )
    cost_center = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="Budget allocation code for expense tracking."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.company.company_name}"


class ProviderCompany(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    company_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    contact_person = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    overall_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    # Provider capabilities (US-37, US-38, US-105)
    service_area = models.TextField(
        blank=True, null=True,
        help_text="Geographic areas this provider covers (e.g. Accra, Tema, Kumasi, Takoradi)."
    )
    specializations = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Comma-separated specializations (e.g. airport,executive,events)."
    )
    response_time_avg = models.DurationField(
        null=True, blank=True,
        help_text="Average response time to quote requests."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name_plural = "Provider Companies"

    def __str__(self):
        return f"{self.company_name} [{self.get_status_display()}]"


