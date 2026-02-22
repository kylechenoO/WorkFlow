"""
Syslog Viewer Views

Provides the syslog listing page with filtering capabilities.
"""

## import buildin pkgs
from datetime import datetime

## import django pkgs
from django.shortcuts import render
from django.core.paginator import Paginator
from urllib.parse import urlencode

from .models import WfSyslog
from accounts.decorators import require_permission


def _parse_datetime(value):
    """
    Parse datetime string from datetime-local input.

    Supports formats: YYYY-MM-DDTHH:MM, YYYY-MM-DD HH:MM, YYYY-MM-DD
    Returns datetime object or None.
    """

    if not value:
        return None

    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


@require_permission('syslog', 'view')
def syslog_list(request):
    """
    Display workflow system log entries with optional filters.

    Supports filtering by level, date range (with time), and text search.
    """

    ## base queryset
    qs = WfSyslog.objects.order_by('-created_at')

    ## apply filters
    filter_level = request.GET.get('level', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')
    filter_search = request.GET.get('search', '')

    if filter_level:
        qs = qs.filter(level=filter_level)

    dt_from = _parse_datetime(filter_date_from)
    if dt_from:
        qs = qs.filter(created_at__gte=dt_from)

    dt_to = _parse_datetime(filter_date_to)
    if dt_to:
        qs = qs.filter(created_at__lte=dt_to)

    if filter_search:
        qs = qs.filter(message__icontains=filter_search)

    ## paginate
    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    ## log levels for filter dropdown
    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    ## build filter_query for pagination links
    filter_query = urlencode({k: v for k, v in {
        'level': filter_level,
        'date_from': filter_date_from,
        'date_to': filter_date_to,
        'search': filter_search,
    }.items() if v})

    context = {
        'nav_active': 'syslog',
        'entries': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
        'filter_query': filter_query,
        'levels': levels,
        'filter_level': filter_level,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'filter_search': filter_search,
    }

    return render(request, 'syslog_viewer/syslog_list.html', context)
