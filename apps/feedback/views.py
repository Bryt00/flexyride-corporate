"""Feedback, rating, and support incident ticketing views."""
from decimal import Decimal
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from bookings.models import TransportationRequest
from feedback.models import JourneyRating, BookingTimeline, SupportIssue
from sla.models import SLAMetric
from portal.selectors import _get_customer_company
from portal.views.base import is_corporate


@login_required
@user_passes_test(is_corporate)
def submit_journey_rating_view(request):
    """Submits a customer star rating and feedback review for a completed journey (US-35, US-101)."""
    if request.method != 'POST':
        return redirect('portal_trip_history')

    request_number = request.POST.get('request_number')
    try:
        rating_val = int(request.POST.get('rating', 5))
    except (ValueError, TypeError):
        rating_val = 5
    comments = request.POST.get('comments', '')

    company = _get_customer_company(request.user)
    req = get_object_or_404(TransportationRequest, request_number=request_number, customer=company)

    JourneyRating.objects.update_or_create(
        request=req,
        defaults={
            'rating': rating_val,
            'comments': comments,
            'rated_by': request.user,
            'passenger_name': request.user.get_full_name() or request.user.username
        }
    )

    assignment = req.vehicle_assignments.first()
    if assignment and assignment.vehicle and assignment.vehicle.provider:
        provider = assignment.vehicle.provider
        ratings = JourneyRating.objects.filter(request__vehicle_assignments__vehicle__provider=provider)
        avg_score = sum(r.rating for r in ratings) / max(len(ratings), 1)
        today = timezone.now().date()
        SLAMetric.objects.create(
            provider=provider,
            metric_type=SLAMetric.MetricType.CUSTOMER_SATISFACTION,
            value=Decimal(str(round(avg_score * 20, 2))),
            period_start=today.replace(day=1),
            period_end=today
        )

    messages.success(request, f"Thank you! Your {rating_val}-star review for trip {req.request_number} has been recorded.")
    return redirect('portal_trip_history')


@login_required
def report_support_issue_view(request):
    """Reports a support or operational incident tied to a journey (US-32, US-36, US-65)."""
    if request.method != 'POST':
        return redirect('portal_dashboard')

    request_number = request.POST.get('request_number')
    issue_type = request.POST.get('issue_type', 'OTHER')
    description = request.POST.get('description', '')

    req = TransportationRequest.objects.filter(request_number=request_number).first()
    if req:
        issue = SupportIssue.objects.create(
            request=req,
            issue_type=issue_type,
            description=description,
            reported_by=request.user,
            status=SupportIssue.Status.OPEN
        )
        BookingTimeline.objects.create(
            request=req,
            action_type='ISSUE_REPORTED',
            actor=request.user,
            description=f"Support issue reported: {issue.get_issue_type_display()} - {description[:80]}"
        )
        messages.success(request, f"Support ticket #{issue.id} lodged with FlexyRide Dispatch Desk. An operations officer has been alerted.")

        next_url = request.POST.get('next_url')
        if next_url:
            return redirect(next_url)
        return redirect('portal_request_details', request_id=req.request_number)

    messages.error(request, "Transportation request not found.")
    return redirect('portal_dashboard')
