"""
Audit Models

Defines the AuditLog model for tracking all user actions
across the WorkFlow web frontend.
"""

## import django pkgs
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Audit log entry for tracking user actions.

    Every significant action (create, update, delete, enable, disable,
    run, login, logout) is recorded with the user, target, and details.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=32)
    target_type = models.CharField(max_length=32)
    target_name = models.CharField(max_length=128)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wf_audit_log'
        ordering = ['-created_at']

    def __str__(self):
        return '[%s] %s %s:%s' % (
            self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            self.action,
            self.target_type,
            self.target_name,
        )

    @classmethod
    def log(cls, user=None, action='', target_type='', target_name='',
            detail=None, ip_address=None):
        """
        Create an audit log entry.

        Args:
            user: Django User instance or None
            action (str): Action performed (create, update, delete, etc.)
            target_type (str): Type of target (flow, user, group, role)
            target_name (str): Name/identifier of the target
            detail (dict): Additional details
            ip_address (str): Client IP address

        Returns:
            AuditLog: Created audit log entry
        """

        try:
            entry = cls.objects.create(
                user=user,
                action=action,
                target_type=target_type,
                target_name=target_name,
                detail=detail or {},
                ip_address=ip_address,
            )
            return entry
        except Exception:
            ## fail silently — audit logging should never break the app
            return None
