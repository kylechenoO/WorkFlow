"""
System Middleware

TimezoneMiddleware — activates the system timezone from database settings.
RequestLogMiddleware — logs every HTTP request to wf_reqlog for the
frontend service log panel.
PasswordExpiryMiddleware — forces password change when expired.
"""

## import buildin pkgs
import json
import time
import zoneinfo

## import django pkgs
from django.db import connection
from django.utils import timezone


## =============================================================
## Module-level cache to avoid DB query on every request
## =============================================================

_cache = {
    'timezone': None,
    'expires': 0,
}

## cache TTL in seconds
_CACHE_TTL = 30


def _clear_cache():
    """Clear the timezone cache (called after settings change)."""
    _cache['timezone'] = None
    _cache['expires'] = 0


def _get_cached_timezone():
    """Get timezone string from cache or DB."""
    now = time.time()
    if _cache['timezone'] is not None and now < _cache['expires']:
        return _cache['timezone']

    try:
        from system.models import SystemSetting
        tz = SystemSetting.get('timezone', 'UTC')
    except Exception:
        tz = 'UTC'

    _cache['timezone'] = tz
    _cache['expires'] = now + _CACHE_TTL
    return tz


## =============================================================
## Middleware
## =============================================================

class TimezoneMiddleware:
    """
    Activate the system-configured timezone on each request.

    Django uses this to render datetimes in templates with
    the correct timezone offset.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = _get_cached_timezone()
        try:
            tz_info = zoneinfo.ZoneInfo(tz_name)
            timezone.activate(tz_info)
        except Exception:
            timezone.deactivate()

        response = self.get_response(request)
        return response


## =============================================================
## Request Log Middleware
## =============================================================

## paths to skip (high-volume static assets)
_REQLOG_SKIP = ('/static/', '/favicon.')


class RequestLogMiddleware:
    """
    Log every HTTP request to wf_reqlog for the frontend service log panel.

    Captures method, path, status code, and duration. Uses raw SQL insert
    for lightweight writes. Silently ignores errors to never break requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ## skip static files
        path = request.path
        for prefix in _REQLOG_SKIP:
            if path.startswith(prefix):
                return self.get_response(request)

        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)

        try:
            status_code = response.status_code
            if status_code >= 500:
                level = 'ERROR'
            elif status_code >= 400:
                level = 'WARNING'
            else:
                level = 'INFO'

            method = request.method
            message = json.dumps({
                'method': method,
                'path': path,
                'status': status_code,
                'duration_ms': duration_ms,
            }, ensure_ascii=False)

            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO wf_reqlog (level, method, path, status, duration_ms, message)"
                    " VALUES (%s, %s, %s, %s, %s, %s)",
                    (level, method, path[:512], status_code, duration_ms, message)
                )
        except Exception:
            pass

        return response


## =============================================================
## Password Expiry Middleware
## =============================================================

## module-level cache for password expiry setting
_pw_cache = {
    'expiry_days': None,
    'expires': 0,
}


def _get_cached_expiry_days():
    """Get password_expiry_days from cache or DB."""
    now = time.time()
    if _pw_cache['expiry_days'] is not None and now < _pw_cache['expires']:
        return _pw_cache['expiry_days']

    try:
        from system.models import SystemSetting
        val = int(SystemSetting.get('password_expiry_days', '0'))
    except Exception:
        val = 0

    _pw_cache['expiry_days'] = val
    _pw_cache['expires'] = now + _CACHE_TTL
    return val


## paths exempt from password expiry redirect
_PW_EXEMPT = ('/accounts/login/', '/accounts/logout/', '/accounts/change-password/', '/static/', '/favicon.')


class PasswordExpiryMiddleware:
    """
    Force password change when the user's password has expired.

    Checks password_expiry_days setting against the user's
    password_changed_at timestamp. Redirects to change-password
    page if expired. Blocks ALL other pages until the user
    changes their password.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ## skip exempt paths
            path = request.path
            for exempt in _PW_EXEMPT:
                if path.startswith(exempt):
                    return self.get_response(request)

            ## check expiry setting
            expiry_days = _get_cached_expiry_days()
            if expiry_days > 0:
                try:
                    from accounts.models import UserProfile
                    from datetime import timedelta

                    try:
                        profile = UserProfile.objects.get(user=request.user)
                        changed_at = profile.password_changed_at
                    except UserProfile.DoesNotExist:
                        changed_at = None

                    ## expired if no record or older than expiry_days
                    if changed_at is None or (timezone.now() - changed_at > timedelta(days=expiry_days)):
                        from django.shortcuts import redirect
                        from django.contrib import messages
                        messages.warning(request, 'Your password has expired. Please set a new password.')
                        return redirect('/accounts/change-password/')

                except Exception:
                    pass

        return self.get_response(request)
