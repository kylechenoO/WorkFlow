"""
Audit Middleware

Automatically captures POST/PUT/DELETE requests and logs
them to the audit trail.
"""

## import buildin pkgs
import json
import logging

## import django pkgs
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware that auto-captures mutating HTTP requests
    (POST, PUT, DELETE) and logs them to the AuditLog model.

    Skips static files, admin, and other exempt paths.
    Views that handle their own audit logging should work fine
    alongside this middleware (duplicate entries are acceptable
    as the middleware provides a safety net).
    """

    EXEMPT_PATHS = [
        '/static/',
        '/favicon.ico',
        '/admin/',
        '/accounts/login/',
    ]

    METHODS = ('POST', 'PUT', 'DELETE')

    def process_response(self, request, response):
        """Log mutating requests after response is generated."""

        try:
            ## skip non-mutating methods
            if request.method not in self.METHODS:
                return response

            ## skip unauthenticated users
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return response

            ## skip exempt paths
            path = request.path
            for exempt in self.EXEMPT_PATHS:
                if path.startswith(exempt):
                    return response

            ## skip failed requests (4xx, 5xx)
            if response.status_code >= 400:
                return response

            ## parse action from URL path
            action = self._parse_action(request.method, path)
            target_type, target_name = self._parse_target(path)

            ## build detail
            detail = {
                'method': request.method,
                'path': path,
                'status_code': response.status_code,
            }

            ## try to capture request body summary (not for file uploads)
            content_type = request.content_type or ''
            if 'json' in content_type or 'form' in content_type:
                try:
                    body = request.body.decode('utf-8', errors='replace')[:500]
                    detail['body_preview'] = body
                except Exception:
                    pass

            ## lazy import to avoid circular dependency
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action=action,
                target_type=target_type,
                target_name=target_name,
                detail=detail,
                ip_address=request.META.get('REMOTE_ADDR'),
            )

        except Exception as e:
            ## audit logging must never break the app
            logger.warning('AuditMiddleware error: %s' % (e))

        return response

    def _parse_action(self, method, path):
        """Derive action name from HTTP method and URL path."""

        ## check for specific action keywords in path
        path_lower = path.lower()

        action_keywords = ['enable', 'disable', 'delete', 'toggle', 'rename', 'run']
        for keyword in action_keywords:
            if keyword in path_lower:
                return keyword

        ## fallback to method-based action
        method_map = {
            'POST': 'create',
            'PUT': 'update',
            'DELETE': 'delete',
        }
        return method_map.get(method, method.lower())

    def _parse_target(self, path):
        """Derive target type and name from URL path."""

        parts = [p for p in path.strip('/').split('/') if p]

        ## /workflows/<name>/... → type=flow, name=<name>
        if len(parts) >= 2 and parts[0] == 'workflows':
            return 'flow', parts[1]

        ## /accounts/users/<id>/... → type=user, name=<id>
        if len(parts) >= 3 and parts[0] == 'accounts':
            return parts[1].rstrip('s'), parts[2] if len(parts) > 2 else ''

        ## /audit/ → type=audit
        if parts:
            return parts[0], parts[1] if len(parts) > 1 else ''

        return 'unknown', ''
