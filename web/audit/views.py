"""
Audit Views

Provides the audit log listing page with filtering capabilities.
"""

## import django pkgs
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .models import AuditLog


@login_required
def audit_list(request):
    """
    Display audit log entries with optional filters.

    Supports filtering by user, action, target_type, and date range.
    """

    ## base queryset
    qs = AuditLog.objects.select_related('user').order_by('-created_at')

    ## apply filters
    filter_user = request.GET.get('user', '')
    filter_action = request.GET.get('action', '')
    filter_target = request.GET.get('target_type', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')
    filter_search = request.GET.get('search', '')

    if filter_user:
        qs = qs.filter(user__username=filter_user)

    if filter_action:
        qs = qs.filter(action=filter_action)

    if filter_target:
        qs = qs.filter(target_type=filter_target)

    if filter_date_from:
        qs = qs.filter(created_at__date__gte=filter_date_from)

    if filter_date_to:
        qs = qs.filter(created_at__date__lte=filter_date_to)

    if filter_search:
        qs = qs.filter(target_name__icontains=filter_search)

    ## limit to 500 entries
    entries = qs[:500]

    ## build filter options
    users = User.objects.values_list('username', flat=True).order_by('username')
    actions = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
    target_types = AuditLog.objects.values_list('target_type', flat=True).distinct().order_by('target_type')

    context = {
        'nav_active': 'audit',
        'entries': entries,
        'users': users,
        'actions': actions,
        'target_types': target_types,
        'filter_user': filter_user,
        'filter_action': filter_action,
        'filter_target': filter_target,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'filter_search': filter_search,
    }

    return render(request, 'audit/audit_list.html', context)
