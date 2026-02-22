"""
Dashboard Views

Provides the home dashboard view with summary statistics.
"""

## import django pkgs
from django.shortcuts import render
from django.contrib.auth.models import User
from django.core.paginator import Paginator

from accounts.decorators import require_permission


@require_permission('dashboard', 'view')
def home(request):
    """
    Dashboard home page.

    Shows summary counts for workflows, users, and recent workflows.
    """

    ## lazy imports to avoid circular dependencies
    from workflows.models import WfFlow

    ## gather stats
    flow_count = WfFlow.objects.filter(deleted=False).count()
    flow_enabled = WfFlow.objects.filter(deleted=False, enabled=True).count()
    flow_disabled = WfFlow.objects.filter(deleted=False, enabled=False).count()
    user_count = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    ## workflows sorted by updated_at desc, paginated
    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    all_flows = WfFlow.objects.filter(deleted=False).order_by('-updated_at')
    flow_paginator = Paginator(all_flows, per_page)
    recent_flows = flow_paginator.get_page(request.GET.get('page', 1))

    context = {
        'nav_active': 'dashboard',
        'flow_count': flow_count,
        'flow_enabled': flow_enabled,
        'flow_disabled': flow_disabled,
        'user_count': user_count,
        'active_users': active_users,
        'recent_flows': recent_flows,
        'page_obj': recent_flows,
        'per_page': per_page,
        'total_count': flow_paginator.count,
    }

    return render(request, 'dashboard/home.html', context)
