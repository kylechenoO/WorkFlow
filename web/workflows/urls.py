"""
Workflows URL Configuration
"""

## import django pkgs
from django.urls import path
from . import views

app_name = 'workflows'

urlpatterns = [
    path('', views.flow_list, name='flow_list'),
    path('runs/', views.run_history_all, name='run_history_all'),
    path('create/', views.flow_create, name='flow_create'),
    path('<str:flow_name>/edit/', views.flow_edit, name='flow_edit'),
    path('<str:flow_name>/delete/', views.flow_delete, name='flow_delete'),
    path('<str:flow_name>/enable/', views.flow_enable, name='flow_enable'),
    path('<str:flow_name>/disable/', views.flow_disable, name='flow_disable'),
    path('<str:flow_name>/run/', views.flow_run, name='flow_run'),
    path('<str:flow_name>/run/<int:run_id>/', views.flow_run_detail, name='flow_run_detail'),
    path('<str:flow_name>/runs/', views.flow_run_history, name='flow_run_history'),
    path('<str:flow_name>/rename/', views.flow_rename, name='flow_rename'),
    ## version history urls
    path('<str:flow_name>/versions/', views.flow_versions, name='flow_versions'),
    path('<str:flow_name>/versions/<int:version_id>/', views.flow_version_detail, name='flow_version_detail'),
    path('<str:flow_name>/versions/diff/', views.flow_version_diff, name='flow_version_diff'),
    path('<str:flow_name>/versions/<int:version_id>/restore/', views.flow_version_restore, name='flow_version_restore'),
]
