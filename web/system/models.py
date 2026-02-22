"""
System Settings Models

Key-value store for system-wide configuration settings.
"""

## import buildin pkgs
import hashlib
import secrets

## import django pkgs
from django.db import models


class SystemSetting(models.Model):
    """
    Generic key-value store for system settings.

    Used for timezone, and extensible for future system configs.
    """

    key = models.CharField(max_length=128, unique=True)
    value = models.TextField(default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_setting'

    def __str__(self):
        return '%s = %s' % (self.key, self.value)

    @classmethod
    def get(cls, key, default=''):
        """Get a setting value by key, returning default if not found."""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
        except Exception:
            return default

    @classmethod
    def set(cls, key, value):
        """Set a setting value by key (create or update)."""
        obj, created = cls.objects.update_or_create(
            key=key,
            defaults={'value': value},
        )
        return obj


class ApiKey(models.Model):
    """Platform API key for programmatic access."""

    name        = models.CharField(max_length=128)
    key_prefix  = models.CharField(max_length=8)    ## first 8 chars shown in UI (wf_xxxxx)
    key_hash    = models.CharField(max_length=64)    ## SHA-256 of full key, never stored plain
    created_by  = models.CharField(max_length=150)
    last_used   = models.DateTimeField(null=True, blank=True)
    enabled     = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_api_key'
        ordering = ['-created_at']

    def __str__(self):
        return '%s (%s...)' % (self.name, self.key_prefix)

    @classmethod
    def generate(cls, name, created_by):
        """Generate a new API key, returning (instance, plain_key)."""
        plain = 'wf_' + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain.encode()).hexdigest()
        inst = cls.objects.create(
            name=name,
            key_prefix=plain[:8],
            key_hash=key_hash,
            created_by=created_by,
        )
        return inst, plain

    @classmethod
    def verify(cls, plain_key):
        """Return enabled ApiKey if key matches, else None."""
        if not plain_key:
            return None
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        try:
            from django.utils import timezone
            key = cls.objects.get(key_hash=key_hash, enabled=True)
            key.last_used = timezone.now()
            key.save(update_fields=['last_used'])
            return key
        except cls.DoesNotExist:
            return None
        except Exception:
            return None


class WfReqlog(models.Model):
    """
    Unmanaged model mapping to the wf_reqlog table.

    Stores Django HTTP request logs captured by RequestLogMiddleware.
    Django creates the records; the table DDL is in tools/workflow.ddl.sql.
    """

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=16)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=512)
    status = models.IntegerField(default=0)
    duration_ms = models.IntegerField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'wf_reqlog'
        ordering = ['-created_at']

    def __str__(self):
        return '[%s] %s %s %d' % (self.level, self.method, self.path, self.status)


class DevtoolRequest(models.Model):
    """
    Persists RESTFultool request/response history per user.
    """

    user        = models.CharField(max_length=150)
    method      = models.CharField(max_length=10)
    url         = models.TextField()
    headers     = models.JSONField(default=dict)
    body        = models.TextField(blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    response    = models.TextField(blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_devtool_request'
        ordering = ['-created_at']

    def __str__(self):
        return '%s %s (%s)' % (self.method, self.url, self.user)
