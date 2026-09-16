from django.urls import path
from . import views

app_name = 'fleet'

urlpatterns = [
    path('categories/', views.fleet_categories_view, name='categories'),
    path('providers/', views.broker_providers_view, name='broker_providers'),
    path('provider/fleet/', views.provider_fleet_view, name='provider_fleet'),
    path('provider/drivers/', views.provider_drivers_view, name='provider_drivers'),
]
