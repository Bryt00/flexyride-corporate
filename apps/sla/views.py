"""SLA compliance and performance analytics views."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from portal.views.base import is_admin


@login_required
@user_passes_test(is_admin)
def admin_metrics_view(request):
    """System Administrator SLA Metrics & Compliance Dashboard."""
    return render(request, 'sla/admin_metrics.html', {
        'active_tab': 'admin_metrics',
        'role_title': 'System Administrator'
    })
