"""Authentication and account profile views for corporate users."""
from django.shortcuts import render, redirect
from django.contrib.auth import logout, login, update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse_lazy
from django.contrib import messages

from accounts.models import User, CorporateCustomer, CompanyEmployee
from portal.forms import CorporateCustomerSignUpForm
from portal.selectors import _get_customer_company
from portal.views.base import is_corporate


class RoleBasedLoginView(LoginView):
    """Screen 1: Split-screen Corporate Login Page."""
    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_sidebar'] = True
        context['hide_navbar'] = True
        return context

    def get_success_url(self):
        user = self.request.user
        url = self.get_redirect_url()
        if url and not (url.endswith('/dashboard/') and (user.is_superuser or user.role in [User.Role.SYSTEM_ADMIN, User.Role.BROKER])):
            return url

        if user.is_superuser or user.role == User.Role.SYSTEM_ADMIN:
            return reverse_lazy('portal_broker_workspace')
        elif user.role == User.Role.BROKER:
            return reverse_lazy('portal_broker_workspace')
        elif user.role == User.Role.PROVIDER_ADMIN:
            return reverse_lazy('portal_provider_workspace')
        elif user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]:
            return reverse_lazy('portal_dashboard')
        return reverse_lazy('portal_dashboard')


def portal_logout_view(request):
    """Logout handler supporting both GET and POST requests."""
    logout(request)
    return redirect('portal_login')


def customer_signup_view(request):
    """Public self-service corporate customer registration view."""
    if request.user.is_authenticated:
        if request.user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]:
            return redirect('portal_dashboard')
        elif request.user.role == User.Role.PROVIDER_ADMIN:
            return redirect('portal_provider_workspace')
        elif request.user.role == User.Role.BROKER:
            return redirect('portal_broker_workspace')
        return redirect('portal_dashboard')

    if request.method == 'POST':
        form = CorporateCustomerSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user, customer = form.save()
            login(request, user, backend='accounts.backends.EmailOrUsernameModelBackend')
            messages.success(
                request,
                f"Welcome to FlexyRide Corporate, {user.first_name}! Your account has been created. "
                "Please complete your profile and upload your corporate brand logo below to personalize your navbar."
            )
            return redirect('portal_customer_profile')
    else:
        form = CorporateCustomerSignUpForm()

    return render(request, 'accounts/signup.html', {
        'form': form,
        'hide_sidebar': True,
        'hide_navbar': False,
    })


@login_required
@user_passes_test(is_corporate)
def customer_profile_view(request):
    """Dedicated Corporate Customer Profile & Settings."""
    company = _get_customer_company(request.user)
    employee = getattr(request.user, 'employee_profile', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_personal_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            department = request.POST.get('department', '').strip()

            if first_name and last_name and email:
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.phone_number = phone_number
                request.user.save()

                if employee:
                    employee.department = department
                    employee.save()

                messages.success(request, "Your personal details were successfully saved.")
            else:
                messages.error(request, "First name, last name, and email cannot be empty.")
            return redirect('portal_customer_profile')

        elif action == 'upload_company_logo':
            if company:
                logo_file = request.FILES.get('company_logo') or request.FILES.get('logo')
                if logo_file:
                    company.logo = logo_file
                    company.save()
                    messages.success(request, "Company brand logo uploaded successfully! Your navbar has been updated.")
                else:
                    messages.error(request, "Please select an image file to upload.")
            return redirect('portal_customer_profile')

        elif action == 'remove_company_logo':
            if company and company.logo:
                company.logo.delete(save=False)
                company.logo = None
                company.save()
                messages.success(request, "Corporate logo removed. Company initials badge is now active.")
            return redirect('portal_customer_profile')

        elif action == 'update_company_profile':
            if company:
                if 'logo' in request.FILES or 'company_logo' in request.FILES:
                    company.logo = request.FILES.get('logo') or request.FILES.get('company_logo')
                elif request.POST.get('remove_logo') == '1':
                    company.logo.delete(save=False)
                    company.logo = None

                company_name = request.POST.get('company_name', '').strip()
                registration_number = request.POST.get('registration_number', '').strip()
                tax_id = request.POST.get('tax_id', '').strip()
                contact_email = request.POST.get('contact_email', '').strip()
                contact_phone = request.POST.get('contact_phone', '').strip()
                address = request.POST.get('address', '').strip()

                if company_name and contact_email and contact_phone:
                    company.company_name = company_name
                    company.registration_number = registration_number
                    company.tax_id = tax_id
                    company.contact_email = contact_email
                    company.contact_phone = contact_phone
                    company.address = address
                    company.save()
                    messages.success(request, f"Company information for {company.company_name} updated successfully.")
                else:
                    messages.error(request, "Company name, billing email, and phone are required.")
            return redirect('portal_customer_profile')

        elif action == 'change_password':
            curr_pw = request.POST.get('current_password', '')
            new_pw = request.POST.get('new_password', '')
            confirm_pw = request.POST.get('confirm_new_password', '')

            if not request.user.check_password(curr_pw):
                messages.error(request, "The current password entered is incorrect.")
            elif len(new_pw) < 6:
                messages.error(request, "The new password must be at least 6 characters long.")
            elif new_pw != confirm_pw:
                messages.error(request, "New passwords do not match.")
            else:
                request.user.set_password(new_pw)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully. Your new credentials are now active.")
            return redirect('portal_customer_profile')

    return render(request, 'accounts/customer_profile.html', {
        'company': company,
        'employee': employee,
        'active_tab': 'profile',
    })
