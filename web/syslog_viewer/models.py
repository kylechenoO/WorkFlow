"""
Syslog Viewer Models

Defines the WfSyslog unmanaged model for reading
workflow system logs from the database.
"""

## import django pkgs
from django.db import models


class WfSyslog(models.Model):
    """
    Unmanaged model mapping to the wf_syslog table.

    This table is owned by the WorkFlow backend and populated
    by the structured logger. Django only reads from it.
    """

    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    level = models.CharField(max_length=16)
    logger_name = models.CharField(max_length=64)
    message = models.TextField()

    class Meta:
        managed = False
        db_table = 'wf_syslog'
        ordering = ['-created_at']

    def __str__(self):
        return '[%s] %s: %s' % (self.level, self.logger_name, self.message[:80])
