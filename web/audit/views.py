"""
Audit Views

Provides the audit log listing page with filtering capabilities.
"""

## import buildin pkgs
import json
from datetime import datetime

## import django pkgs
from django.shortcuts import render
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from urllib.parse import urlencode

from .models import AuditLog
from accounts.decorators import require_permission


def _parse_datetime(value):
    """Parse datetime string from flatpickr (Y-m-d H:i) or date-only."""

    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@require_permission('audit', 'view')
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

    dt_from = _parse_datetime(filter_date_from)
    if dt_from:
        qs = qs.filter(created_at__gte=dt_from)

    dt_to = _parse_datetime(filter_date_to)
    if dt_to:
        qs = qs.filter(created_at__lte=dt_to)

    if filter_search:
        qs = qs.filter(
            Q(target_name__icontains=filter_search) |
            Q(action__icontains=filter_search) |
            Q(target_type__icontains=filter_search) |
            Q(user__username__icontains=filter_search) |
            Q(ip_address__icontains=filter_search)
        )

    ## paginate
    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    ## pre-serialize detail as JSON string for safe template rendering
    entries = list(page_obj)
    for entry in entries:
        try:
            entry.detail_json = json.dumps(entry.detail, default=str, ensure_ascii=False)
        except Exception:
            entry.detail_json = '{}'

    ## build filter options
    users = User.objects.values_list('username', flat=True).order_by('username')
    actions = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
    target_types = AuditLog.objects.values_list('target_type', flat=True).distinct().order_by('target_type')

    ## build filter_query for pagination links
    filter_query = urlencode({k: v for k, v in {
        'user': filter_user,
        'action': filter_action,
        'target_type': filter_target,
        'date_from': filter_date_from,
        'date_to': filter_date_to,
        'search': filter_search,
    }.items() if v})

    context = {
        'nav_active': 'audit',
        'entries': entries,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
        'filter_query': filter_query,
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
