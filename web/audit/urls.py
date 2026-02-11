"""
Audit URL Configuration
"""

## import django pkgs
from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_list, name='audit_list'),
]
