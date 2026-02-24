"""
System URL Configuration
"""

## import django pkgs
from django.urls import path

from system import views

app_name = 'system'

urlpatterns = [
    path('timezone/',         views.timezone_view,    name='timezone'),
    path('version/',          views.version_view,     name='version'),
    path('license/',          views.license_view,     name='license'),
    path('devtool/',          views.devtool_view,     name='devtool'),
    path('devtool/request/',  views.devtool_request,  name='devtool_request'),
    path('devtool/sql/',      views.devtool_sql,      name='devtool_sql'),

    path('apis/',                                  views.apis_view,       name='apis'),
    path('apis/keys/create/',                      views.api_key_create,  name='api_key_create'),
    path('apis/keys/<int:key_id>/toggle/',         views.api_key_toggle,  name='api_key_toggle'),
    path('apis/keys/<int:key_id>/delete/',         views.api_key_delete,  name='api_key_delete'),

    path('backup/',         views.backup_view,    name='backup'),
    path('backup/create/',  views.backup_create,  name='backup_create'),
    path('backup/restore/', views.backup_restore, name='backup_restore'),

    path('ssl/',                           views.ssl_view,          name='ssl'),
    path('ssl/server/upload/',             views.ssl_server_upload, name='ssl_server_upload'),
    path('ssl/server/toggle/',             views.ssl_server_toggle, name='ssl_server_toggle'),
    path('ssl/server/delete/',             views.ssl_server_delete, name='ssl_server_delete'),

    path('services/',                    views.services_view,   name='services'),
    path('services/<str:svc>/start/',    views.service_start,   name='service_start'),
    path('services/<str:svc>/stop/',     views.service_stop,    name='service_stop'),
    path('services/<str:svc>/restart/',  views.service_restart, name='service_restart'),
    path('services/<str:svc>/status/',   views.service_status,  name='service_status'),
    path('services/<str:svc>/logs/',     views.service_logs,          name='service_logs'),
    path('services/<str:svc>/config/update/', views.service_config_update, name='service_config_update'),

    path('services/ssh-key/upload/', views.ssh_key_upload, name='ssh_key_upload'),
    path('services/ssh-key/delete/', views.ssh_key_delete, name='ssh_key_delete'),

    path('verify-password/',  views.verify_password,  name='verify_password'),
]
