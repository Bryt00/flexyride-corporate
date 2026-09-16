from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('trips/rate/', views.submit_journey_rating_view, name='rate_trip'),
    path('support/report-issue/', views.report_support_issue_view, name='report_issue'),
]
