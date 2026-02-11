"""
Workflows Models

Defines the WfFlow unmanaged model for reading
workflow definitions from the database.
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
