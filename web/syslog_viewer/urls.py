"""
Syslog Viewer URL Configuration
"""

## import django pkgs
from django.urls import path
from . import views

app_name = 'syslog_viewer'

urlpatterns = [
    path('', views.syslog_list, name='syslog_list'),
]
