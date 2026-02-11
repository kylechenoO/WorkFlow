"""
Syslog Viewer Views

Provides the syslog listing page with filtering capabilities.
"""

## import django pkgs
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import WfSyslog


@login_required
def syslog_list(request):
    """
    Display workflow system log entries with optional filters.

    Supports filtering by level, date range, and text search.
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

    if filter_date_from:
        qs = qs.filter(created_at__date__gte=filter_date_from)

    if filter_date_to:
        qs = qs.filter(created_at__date__lte=filter_date_to)

    if filter_search:
        qs = qs.filter(message__icontains=filter_search)

    ## limit to 500 entries
    entries = qs[:500]

    ## log levels for filter dropdown
    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

    context = {
        'nav_active': 'syslog',
        'entries': entries,
        'levels': levels,
        'filter_level': filter_level,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'filter_search': filter_search,
    }

    return render(request, 'syslog_viewer/syslog_list.html', context)
