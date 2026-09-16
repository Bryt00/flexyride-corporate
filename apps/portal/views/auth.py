"""Authentication and onboarding views for FlexyRide Corporate."""
from django.shortcuts import render, redirect
from django.contrib.auth import logout, login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages

from accounts.models import User
from portal.forms import CorporateCustomerSignUpForm


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
    """Logout handler supporting both GET (from top-nav/sidebar links) and POST requests."""
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
