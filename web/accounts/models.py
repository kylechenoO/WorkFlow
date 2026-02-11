"""
Accounts Models

Defines the Role model for custom role management.
Django's built-in User and Group models handle user/group management.
"""

## import django pkgs
from django.db import models


class Role(models.Model):
    """
    Custom role model for workflow access control.

    Extends beyond Django's built-in Group model to provide
    additional metadata for role-based management.
    """

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wf_role'
        ordering = ['name']

    def __str__(self):
        return self.name
