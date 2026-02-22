"""
Modules URL Configuration
"""

## import django pkgs
from django.urls import path
from . import views

app_name = 'modules'

urlpatterns = [
    ## module management
    path('', views.module_list, name='module_list'),
    path('create/', views.module_create, name='module_create'),
    ## category management (must be before wildcard <str:category>/<str:module_name> patterns)
    path('category/create/', views.category_create, name='category_create'),
    path('category/<str:category>/rename/', views.category_rename, name='category_rename'),
    path('category/<str:category>/delete/', views.category_delete, name='category_delete'),
    ## module CRUD (wildcard patterns)
    path('<str:category>/<str:module_name>/edit/', views.module_edit, name='module_edit'),
    path('<str:category>/<str:module_name>/delete/', views.module_delete, name='module_delete'),
    ## version history
    path('<str:category>/<str:module_name>/versions/', views.module_versions, name='module_versions'),
    path('<str:category>/<str:module_name>/versions/<int:version_id>/', views.module_version_detail, name='module_version_detail'),
    path('<str:category>/<str:module_name>/versions/diff/', views.module_version_diff, name='module_version_diff'),
    path('<str:category>/<str:module_name>/versions/<int:version_id>/restore/', views.module_version_restore, name='module_version_restore'),
    ## API
    path('api/registry/', views.api_registry, name='api_registry'),
    path('api/introspect/<str:category>/<str:module_name>/', views.api_introspect, name='api_introspect'),
]
