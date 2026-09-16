from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.RoleBasedLoginView.as_view(), name='login'),
    path('logout/', views.portal_logout_view, name='logout'),
    path('signup/', views.customer_signup_view, name='signup'),
    path('register/', views.customer_signup_view, name='register'),
    path('profile/', views.customer_profile_view, name='profile'),
]
