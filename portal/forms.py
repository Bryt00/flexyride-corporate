from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from accounts.models import User, CorporateCustomer, CompanyEmployee, ProviderCompany


class CorporateCustomerSignUpForm(forms.Form):
    """
    Self-service registration form for new Corporate Clients.
    Provisions CorporateCustomer entity and the initial Corporate Administrator User.
    """
    # Corporate Entity Details
    company_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Apex Energy Ltd / Nestlé Ghana',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    registration_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. CS-98124-2024 (RGD / Registrar General)',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    tax_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. TIN / GRA Tax Identification',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    company_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'billing@company.com',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    company_phone = forms.CharField(
        max_length=25,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '+233 30 200 0000',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    company_address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Headquarters street, building, city (e.g. Airport City, Accra)',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F] resize-none'
        })
    )
    billing_preference = forms.ChoiceField(
        choices=CorporateCustomer.BillingType.choices,
        initial=CorporateCustomer.BillingType.INVOICE,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    company_logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-700 text-xs file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-black file:bg-[#8CC63F] file:text-[#0A0F1D] hover:file:bg-[#73A233]'
        })
    )

    # Administrator Contact & Account Credentials
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Kwame',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Mensah',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        initial='Corporate Administration',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. Procurement / Executive Office / Operations',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. kwame_apex or corporate_admin',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    admin_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'kwame.mensah@company.com',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    admin_phone = forms.CharField(
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+233 24 000 0000',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Minimum 8 characters with letters & numbers',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Repeat your password',
            'class': 'w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'
        })
    )
    terms_agreed = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded text-[#8CC63F] focus:ring-[#8CC63F] border-slate-300'
        })
    )

    def clean_username(self):
        uname = self.cleaned_data.get('username', '').strip().lower()
        if User.objects.filter(username__iexact=uname).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return uname

    def clean_admin_email(self):
        email = self.cleaned_data.get('admin_email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists. Please sign in.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        if pw and confirm and pw != confirm:
            self.add_error('confirm_password', "Passwords do not match.")
        if pw and len(pw) < 6:
            self.add_error('password', "Password must be at least 6 characters long.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        cd = self.cleaned_data

        # 1. Create CorporateCustomer
        reg_no = cd.get('registration_number')
        if not reg_no:
            # Auto-generate unique registration number if left blank
            import random
            reg_no = f"CC-GH-{random.randint(10000, 99999)}"

        customer = CorporateCustomer.objects.create(
            company_name=cd['company_name'].strip(),
            registration_number=reg_no.strip(),
            tax_id=cd.get('tax_id', '').strip(),
            contact_email=cd['company_email'].strip(),
            contact_phone=cd['company_phone'].strip(),
            address=cd['company_address'].strip(),
            logo=cd.get('company_logo'),
            status=CorporateCustomer.Status.APPROVED,
            billing_type=cd.get('billing_preference', CorporateCustomer.BillingType.INVOICE),
            payment_terms_days=30,
            preferred_currency='GHS'
        )

        # 2. Create User account with role CUSTOMER
        user = User.objects.create_user(
            username=cd['username'].strip(),
            email=cd['admin_email'].strip(),
            first_name=cd['first_name'].strip(),
            last_name=cd['last_name'].strip(),
            role=User.Role.CUSTOMER,
            phone_number=cd.get('admin_phone', '').strip(),
            is_verified=True,
            password=cd['password']
        )

        # 3. Create CompanyEmployee linkage (with administrative approval permissions)
        CompanyEmployee.objects.create(
            company=customer,
            user=user,
            can_approve_requests=True,
            spending_limit=15000.00,
            department=cd.get('department', 'Corporate Administration').strip(),
            cost_center='CORP-ADMIN-01'
        )

        return user, customer


class CustomerProfileUpdateForm(forms.ModelForm):
    """Update personal profile details for logged in corporate customer."""
    department = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-mono focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
        }


class CorporateCompanyUpdateForm(forms.ModelForm):
    """Update corporate organization details."""
    class Meta:
        model = CorporateCustomer
        fields = ['company_name', 'registration_number', 'tax_id', 'contact_email', 'contact_phone', 'address', 'logo']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'registration_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-mono focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'tax_id': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-mono focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'contact_email': forms.EmailInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'contact_phone': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F]'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm focus:ring-2 focus:ring-[#8CC63F]/40 focus:border-[#8CC63F] resize-none'}),
            'logo': forms.FileInput(attrs={'accept': 'image/*', 'class': 'w-full px-4 py-2 bg-white border border-slate-200 rounded-xl text-slate-700 text-xs file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-black file:bg-[#8CC63F] file:text-[#0A0F1D] hover:file:bg-[#73A233]'}),
        }
