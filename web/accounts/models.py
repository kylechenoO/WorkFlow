"""
Accounts Models

Defines the Role, Permission, and GroupPermission models
for role/group-based access control.
Django's built-in User and Group models handle user/group management.
"""

## import django pkgs
from django.db import models


class Permission(models.Model):
    """
    Platform permission representing a page + action pair.

    Examples: dashboard.view, workflows.create, users.delete
    Tables managed by raw DDL (wf_permission).
    """

    page = models.CharField(max_length=64)
    action = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wf_permission'
        managed = False
        ordering = ['page', 'action']
        unique_together = [['page', 'action']]

    def __str__(self):
        return '%s.%s' % (self.page, self.action)


class GroupPermission(models.Model):
    """
    Maps Django auth.Group to Permission (M2M junction).

    Table managed by raw DDL (wf_group_permission).
    """

    group = models.ForeignKey(
        'auth.Group',
        on_delete=models.CASCADE,
        db_column='group_id'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        db_column='permission_id'
    )

    class Meta:
        db_table = 'wf_group_permission'
        managed = False
        unique_together = [['group', 'permission']]

    def __str__(self):
        return '%s -> %s' % (self.group.name, self.permission)


class Role(models.Model):
    """
    Custom role model for workflow access control.

    Extends beyond Django's built-in Group model to provide
    additional metadata for role-based management.
    Users can be assigned to roles via the ManyToMany relationship.
    Permissions can be assigned to roles via the permissions M2M.
    """

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, null=True)
    users = models.ManyToManyField(
        'auth.User',
        related_name='wf_roles',
        blank=True,
        db_table='wf_user_role'
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name='roles',
        blank=True,
        db_table='wf_role_permission'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wf_role'
        ordering = ['name']

    def __str__(self):
        return self.name
