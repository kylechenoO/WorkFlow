"""
WorkFlow Web URL Configuration

Root URL configuration that includes all app-level URL patterns.
"""

## import django pkgs
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
]
