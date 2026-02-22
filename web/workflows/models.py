"""
Workflows Models

Defines the WfFlow, WfRunHistory, and WfRunStep unmanaged models
for reading workflow definitions and run history from the database.
"""

## import buildin pkgs
import json

## import django pkgs
from django.db import models


class WfFlow(models.Model):
    """
    Unmanaged model mapping to the wf_flow table.

    This table is owned by the WorkFlow backend. Django reads
    from it for display; all mutations go through the REST API.
    """

    id = models.BigAutoField(primary_key=True)
    flow_name = models.CharField(max_length=128, unique=True)
    flow_procedures = models.JSONField()
    enabled = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'wf_flow'

    def __str__(self):
        return self.flow_name

    def get_procedures(self):
        """
        Return the flow_procedures as a Python dict.

        Handles cases where the field is stored as a JSON string
        or already parsed as a dict.
        """

        if isinstance(self.flow_procedures, str):
            try:
                return json.loads(self.flow_procedures)
            except (json.JSONDecodeError, TypeError):
                return {}
        return self.flow_procedures or {}

    def procedure_count(self):
        """Return the number of procedure steps."""

        procs = self.get_procedures()
        return len(procs.get('procedures', []))


class WfRunHistory(models.Model):
    """
    Unmanaged model mapping to the wf_run_history table.

    Tracks each workflow execution with status, timing,
    and who triggered the run.
    """

    id = models.BigAutoField(primary_key=True)
    flow_name = models.CharField(max_length=128)
    status = models.CharField(max_length=16, default='running')
    trigger_by = models.CharField(max_length=64, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error_msg = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'wf_run_history'
        ordering = ['-start_time']

    def __str__(self):
        return '#%d %s [%s]' % (self.id, self.flow_name, self.status)


class WfRunStep(models.Model):
    """
    Unmanaged model mapping to the wf_run_step table.

    Tracks individual step execution within a workflow run,
    including timing, result data, and error info.
    """

    id = models.BigAutoField(primary_key=True)
    run = models.ForeignKey(
        WfRunHistory,
        on_delete=models.CASCADE,
        db_column='run_id',
        related_name='steps'
    )
    step_name = models.CharField(max_length=128)
    step_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, default='pending')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    result_data = models.JSONField(null=True, blank=True)
    error_msg = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'wf_run_step'
        ordering = ['step_order']

    def __str__(self):
        return '%s [%s]' % (self.step_name, self.status)


class WfVersion(models.Model):
    """
    Version history entry for workflow and module changes.

    Stores a full content snapshot each time a workflow or module
    is saved, enabling diff comparison and version restoration.
    """

    TYPE_FLOW = 'flow'
    TYPE_MODULE = 'module'
    TYPE_CHOICES = [
        (TYPE_FLOW, 'Workflow'),
        (TYPE_MODULE, 'Module'),
    ]

    id = models.BigAutoField(primary_key=True)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    target_name = models.CharField(max_length=192)
    version = models.PositiveIntegerField()
    content = models.TextField()
    changed_by = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wf_version'
        ordering = ['-version']
        unique_together = [('type', 'target_name', 'version')]

    def __str__(self):
        return '%s:%s v%d' % (self.type, self.target_name, self.version)

    @classmethod
    def create_version(cls, type, target_name, content, changed_by=None):
        """
        Create a new version entry, auto-incrementing the version number.

        Args:
            type (str): 'flow' or 'module'
            target_name (str): flow_name or 'category.ModuleName'
            content (str): Full content snapshot (JSON string or code)
            changed_by (str): Username who made the change

        Returns:
            WfVersion: Created version entry or None on error
        """

        try:
            ## get next version number for this target
            last = cls.objects.filter(
                type=type,
                target_name=target_name,
            ).order_by('-version').first()

            next_version = (last.version + 1) if last else 1

            return cls.objects.create(
                type=type,
                target_name=target_name,
                version=next_version,
                content=content,
                changed_by=changed_by,
            )
        except Exception:
            ## fail silently — version logging should never break the app
            return None

    @classmethod
    def get_history(cls, type, target_name, limit=50):
        """
        Get version history for a target.

        Args:
            type (str): 'flow' or 'module'
            target_name (str): flow_name or 'category.ModuleName'
            limit (int): Maximum entries to return

        Returns:
            QuerySet: Version entries ordered by descending version
        """

        return cls.objects.filter(
            type=type,
            target_name=target_name,
        ).order_by('-version')[:limit]
