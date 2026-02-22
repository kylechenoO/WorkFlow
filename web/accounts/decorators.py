"""
Accounts Decorators

Custom view decorators for permission-based access control.
"""

## import buildin pkgs
from functools import wraps

## import django pkgs
from django.shortcuts import redirect
from django.contrib import messages

from accounts.permissions import has_permission


def require_permission(page, action):
    """
    Decorator that checks if the current user has a specific permission.

    Replaces @login_required — also handles authentication check.
    On failure, redirects to dashboard with an error message.

    Usage:
        @require_permission('workflows', 'create')
        def flow_create(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ## check authentication first
            if not request.user.is_authenticated:
                return redirect('/accounts/login/')

            ## check permission
            if not has_permission(request.user, page, action):
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('/')

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
