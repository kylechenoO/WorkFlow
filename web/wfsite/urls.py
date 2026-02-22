"""
WorkFlow Web URL Configuration

Root URL configuration that includes all app-level URL patterns.
"""

## import django pkgs
from django.conf import settings
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    ## django admin
    path('admin/', admin.site.urls),
    ## project apps
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('audit/', include('audit.urls')),
    path('syslog/', include('syslog_viewer.urls')),
    path('workflows/', include('workflows.urls')),
    path('modules/', include('modules.urls')),
    path('system/', include('system.urls')),
]

## serve static files when running under gunicorn (non-runserver)
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
