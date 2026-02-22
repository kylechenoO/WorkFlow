"""
Accounts Permissions

Permission registry and helper functions for role + group based
access control. Permissions are the union of all role permissions
and all group permissions assigned to a user.
"""


## =============================================================
## Permission Registry — single source of truth
## =============================================================

PERMISSION_REGISTRY = [
    ('dashboard', 'view'),
    ('workflows', 'view'),
    ('workflows', 'create'),
    ('workflows', 'edit'),
    ('workflows', 'delete'),
    ('workflows', 'enable'),
    ('workflows', 'run'),
    ('modules', 'view'),
    ('modules', 'create'),
    ('modules', 'edit'),
    ('modules', 'delete'),
    ('users', 'view'),
    ('users', 'create'),
    ('users', 'edit'),
    ('users', 'toggle'),
    ('groups', 'view'),
    ('groups', 'create'),
    ('groups', 'edit'),
    ('groups', 'delete'),
    ('roles', 'view'),
    ('roles', 'create'),
    ('roles', 'edit'),
    ('roles', 'delete'),
    ('audit', 'view'),
    ('syslog', 'view'),
    ('system', 'edit'),
    ('devtool', 'use'),
]

## default permission sets for seeding
DEFAULT_ADMIN_PERMS = PERMISSION_REGISTRY[:]

DEFAULT_USER_PERMS = [
    ('dashboard', 'view'),
    ('workflows', 'view'),
    ('workflows', 'create'),
    ('workflows', 'edit'),
]


## =============================================================
## Helper Functions
## =============================================================

def get_user_permissions(user):
    """
    Return set of 'page.action' strings for a user.

    Permissions are the union of:
      - all permissions from the user's roles
      - all permissions from the user's groups
    Superusers automatically get all permissions.
    """

    ## superuser gets everything
    if user.is_superuser:
        return {'%s.%s' % (p, a) for p, a in PERMISSION_REGISTRY}

    perms = set()

    try:
        ## role permissions
        from accounts.models import Role
        for role in Role.objects.filter(users=user).prefetch_related('permissions'):
            for p in role.permissions.all():
                perms.add('%s.%s' % (p.page, p.action))

        ## group permissions
        from accounts.models import GroupPermission
        group_ids = list(user.groups.values_list('id', flat=True))
        if group_ids:
            for gp in GroupPermission.objects.filter(group_id__in=group_ids).select_related('permission'):
                perms.add('%s.%s' % (gp.permission.page, gp.permission.action))

    except Exception:
        ## table may not exist yet during initial migration
        pass

    return perms


def has_permission(user, page, action):
    """Check if a user has a specific permission."""

    if user.is_superuser:
        return True

    perms = get_user_permissions(user)
    return '%s.%s' % (page, action) in perms


def get_user_permissions_dict(user):
    """
    Return nested dict for template usage.

    Returns:
        {'workflows': {'view': True, 'create': False, ...}, ...}
    """

    perms = get_user_permissions(user)
    result = {}

    for page, action in PERMISSION_REGISTRY:
        if page not in result:
            result[page] = {}
        result[page][action] = '%s.%s' % (page, action) in perms

    return result
