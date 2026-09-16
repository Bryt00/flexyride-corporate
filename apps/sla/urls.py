from django.urls import path
from . import views

app_name = 'sla'

urlpatterns = [
    path('admin-metrics/', views.admin_metrics_view, name='admin_metrics'),
]
