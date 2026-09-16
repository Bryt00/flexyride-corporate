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

# --------------------------------------------------------------------------
# Diagnostic 500 Handler (Shows exact error traceback on server 500s)
# --------------------------------------------------------------------------
import sys
import traceback
from django.http import HttpResponseServerError

def handler500_diagnostic(request):
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type:
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    else:
        tb_str = "No active Python exception context in sys.exc_info()."
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Server Error (500) - Diagnostic</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; background: #090e17; color: #e2e8f0; padding: 2rem; margin: 0;">
    <div style="max-width: 1000px; margin: 0 auto;">
        <div style="background: #1e293b; border-left: 4px solid #ef4444; padding: 1.5rem; border-radius: 0.75rem; margin-bottom: 1.5rem;">
            <h1 style="color: #f87171; font-size: 1.4rem; margin: 0 0 0.5rem 0;">Internal Server Error (500) Diagnostic</h1>
            <p style="color: #94a3b8; font-size: 0.875rem; margin: 0;">Path: <code>{request.path}</code> | User: <code>{getattr(request, 'user', 'Anonymous')}</code></p>
        </div>
        <div style="background: #0d1527; border: 1px solid #1e293b; border-radius: 0.75rem; padding: 1.5rem; overflow-x: auto;">
            <pre style="color: #fca5a5; font-size: 0.85rem; line-height: 1.6; margin: 0; font-family: monospace;">{tb_str}</pre>
        </div>
    </div>
</body>
</html>"""
    return HttpResponseServerError(html)

handler500 = handler500_diagnostic

