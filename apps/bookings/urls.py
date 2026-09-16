from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('requests/new/', views.new_request_view, name='new_request'),
    path('requests/<str:request_id>/success/', views.request_success_view, name='request_success'),
    path('requests/<str:request_id>/details/', views.request_details_view, name='request_details'),
    path('bookings/<str:booking_id>/confirmed/', views.confirmed_booking_view, name='confirmed_booking'),
    path('bookings/<str:booking_id>/track/', views.live_journey_view, name='live_journey'),
    path('trips/upcoming/', views.upcoming_trips_view, name='upcoming_trips'),
    path('trips/history/', views.trip_history_view, name='trip_history'),
    path('passenger/track/<str:tracking_token>/', views.passenger_tracking_view, name='passenger_tracking'),
    path('broker/dispatches/', views.broker_dispatches_view, name='broker_dispatches'),
    path('provider/dispatches/', views.provider_dispatches_view, name='provider_dispatches'),
]
