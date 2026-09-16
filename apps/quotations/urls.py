from django.urls import path
from . import views

app_name = 'quotations'

urlpatterns = [
    path('request/<str:request_id>/quote/', views.quote_ready_view, name='quote_ready'),
    path('broker/rfqs/', views.broker_rfqs_view, name='broker_rfqs'),
    path('broker/quotes/', views.broker_quotes_view, name='broker_quotes'),
    path('provider/rfqs/', views.provider_rfqs_view, name='provider_rfqs'),
]
