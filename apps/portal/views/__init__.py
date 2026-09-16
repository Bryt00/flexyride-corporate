"""Portal views package.
Re-exports all view classes and functions from their dedicated domain applications.
"""
# Shared base authorization
from portal.views.base import (
    is_corporate,
    is_broker,
    is_provider,
    is_admin,
    can_view_request,
)

# Core portal views
from portal.views.portal_views import (
    landing_page_view,
    solutions_view,
    how_it_works_view,
    dashboard_view,
    broker_overview_view,
    broker_customers_view,
    provider_overview_view,
    provider_company_view,
    provider_profile_view,
    provider_workspace_view,
    admin_seed_ecosystem_view,
)

# Accounts app views
from accounts.views import (
    RoleBasedLoginView,
    portal_logout_view,
    customer_signup_view,
    customer_profile_view,
)

# Bookings app views
from bookings.views import (
    new_request_view,
    request_success_view,
    request_details_view,
    confirmed_booking_view,
    live_journey_view,
    upcoming_trips_view,
    trip_history_view,
    passenger_tracking_view,
    broker_dispatches_view,
    provider_dispatches_view,
)

# Fleet app views
from fleet.views import (
    fleet_categories_view,
    broker_providers_view,
    provider_fleet_view,
    provider_drivers_view,
)

# Quotations app views
from quotations.views import (
    quote_ready_view,
    broker_rfqs_view,
    broker_quotes_view,
    provider_rfqs_view,
)

# Payments app views
from payments.views import (
    payment_view,
    payment_success_view,
    customer_invoices_view,
    receipt_printable_view,
    invoice_printable_view,
    paystack_webhook_view,
    broker_financials_view,
    provider_payouts_view,
)

# Compliance app views
from compliance.views import (
    compliance_safety_view,
    provider_compliance_view,
)

# Feedback app views
from feedback.views import (
    submit_journey_rating_view,
    report_support_issue_view,
)

# Notifications app views
from notifications.views import (
    webpush_subscribe_api,
    notifications_api,
)

# SLA app views
from sla.views import (
    admin_metrics_view,
)

# Legacy CBVs
from portal.views.customer import (
    HomeView,
    LogoutView,
    CorporateCustomerListView,
    CorporateCustomerDetailView,
    ProviderListView,
    ProviderDetailView,
    RequestListView,
    RequestDetailView,
)

__all__ = [
    # Auth & permissions
    'is_corporate',
    'is_broker',
    'is_provider',
    'is_admin',
    'can_view_request',
    # Public & landing
    'landing_page_view',
    'solutions_view',
    'how_it_works_view',
    'fleet_categories_view',
    'compliance_safety_view',
    'passenger_tracking_view',
    # Authentication
    'RoleBasedLoginView',
    'portal_logout_view',
    'customer_signup_view',
    # Customer
    'dashboard_view',
    'new_request_view',
    'request_success_view',
    'request_details_view',
    'quote_ready_view',
    'payment_view',
    'payment_success_view',
    'confirmed_booking_view',
    'live_journey_view',
    'upcoming_trips_view',
    'trip_history_view',
    'customer_invoices_view',
    'customer_profile_view',
    'HomeView',
    'LogoutView',
    'CorporateCustomerListView',
    'CorporateCustomerDetailView',
    'ProviderListView',
    'ProviderDetailView',
    'RequestListView',
    'RequestDetailView',
    # Broker
    'broker_overview_view',
    'broker_rfqs_view',
    'broker_quotes_view',
    'broker_dispatches_view',
    'broker_providers_view',
    'broker_customers_view',
    'broker_financials_view',
    # Provider
    'provider_overview_view',
    'provider_dispatches_view',
    'provider_rfqs_view',
    'provider_fleet_view',
    'provider_drivers_view',
    'provider_compliance_view',
    'provider_payouts_view',
    'provider_company_view',
    'provider_profile_view',
    'provider_workspace_view',
    # Operations
    'admin_metrics_view',
    'admin_seed_ecosystem_view',
    'paystack_webhook_view',
    'webpush_subscribe_api',
    'notifications_api',
    'submit_journey_rating_view',
    'report_support_issue_view',
    'receipt_printable_view',
    'invoice_printable_view',
]
