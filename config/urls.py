"""
URL configuration for flexyride_corporate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# FlexyRide Corporate Admin Configuration
admin.site.site_header = "FlexyRide Corporate Administration"
admin.site.site_title = "FlexyRide Corporate Admin"
admin.site.index_title = "Executive Management Console"

from django.views.generic.base import RedirectView

from apps.portal import views as portal_views

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/portal/img/logo_icon.png', permanent=False)),
    path('admin/seed-ecosystem/', portal_views.admin_seed_ecosystem_view, name='admin_seed_ecosystem'),
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
    path('portal/', include('portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()

