from django.urls import path
from . import views

app_name = 'compliance'

urlpatterns = [
    path('standards/', views.compliance_safety_view, name='safety_standards'),
    path('provider/vault/', views.provider_compliance_view, name='provider_vault'),
]
