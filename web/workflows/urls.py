"""
Workflows URL Configuration
"""

## import django pkgs
from django.urls import path
from . import views

app_name = 'workflows'

urlpatterns = [
    path('', views.flow_list, name='flow_list'),
    path('create/', views.flow_create, name='flow_create'),
    path('<str:flow_name>/edit/', views.flow_edit, name='flow_edit'),
    path('<str:flow_name>/delete/', views.flow_delete, name='flow_delete'),
    path('<str:flow_name>/enable/', views.flow_enable, name='flow_enable'),
    path('<str:flow_name>/disable/', views.flow_disable, name='flow_disable'),
    path('<str:flow_name>/run/', views.flow_run, name='flow_run'),
    path('<str:flow_name>/rename/', views.flow_rename, name='flow_rename'),
]
