"""
Accounts Context Processors

Injects permission data into all template contexts so templates
can conditionally show/hide sidebar links and action buttons.
"""

from accounts.permissions import get_user_permissions_dict


def user_permissions(request):
    """
    Add perms_map to template context.

    Usage in templates:
        {% if perms_map.workflows.create %}
            <a href="...">Create Workflow</a>
        {% endif %}
    """

    if request.user.is_authenticated:
        return {
            'perms_map': get_user_permissions_dict(request.user),
        }

    return {
        'perms_map': {},
    }
