"""
Dashboard Views

Provides the home dashboard view with summary statistics.
"""

## import django pkgs
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


@login_required
def home(request):
    """
    Dashboard home page.

    Shows summary counts for workflows, users, and recent audit entries.
    """

    ## lazy imports to avoid circular dependencies
    from workflows.models import WfFlow
    from audit.models import AuditLog

    ## gather stats
    flow_count = WfFlow.objects.filter(deleted=False).count()
    flow_enabled = WfFlow.objects.filter(deleted=False, enabled=True).count()
    flow_disabled = WfFlow.objects.filter(deleted=False, enabled=False).count()
    user_count = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    ## recent audit entries
    recent_audit = AuditLog.objects.select_related('user').order_by('-created_at')[:10]

    context = {
        'nav_active': 'dashboard',
        'flow_count': flow_count,
        'flow_enabled': flow_enabled,
        'flow_disabled': flow_disabled,
        'user_count': user_count,
        'active_users': active_users,
        'recent_audit': recent_audit,
    }

    return render(request, 'dashboard/home.html', context)
