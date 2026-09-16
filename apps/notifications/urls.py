from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('api/webpush/subscribe/', views.webpush_subscribe_api, name='webpush_subscribe'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
]
