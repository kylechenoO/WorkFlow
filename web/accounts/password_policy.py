"""
Password Policy

Validates passwords against the system-wide password policy
stored in SystemSetting.
"""

__author__  = 'Kyle'
__version__ = '0.0.1'
__email__   = ''

## import buildin pkgs
import re


def get_password_policy():
    """
    Load the current password policy from SystemSetting.

    Returns:
        dict: { 'min_length': int, 'require_uppercase': bool,
                'require_lowercase': bool, 'require_digit': bool,
                'require_special': bool, 'expiry_days': int }
    """

    from system.models import SystemSetting

    return {
        'min_length': int(SystemSetting.get('password_min_length', '8')),
        'require_uppercase': SystemSetting.get('password_require_uppercase', 'false') == 'true',
        'require_lowercase': SystemSetting.get('password_require_lowercase', 'false') == 'true',
        'require_digit': SystemSetting.get('password_require_digit', 'false') == 'true',
        'require_special': SystemSetting.get('password_require_special', 'false') == 'true',
        'expiry_days': int(SystemSetting.get('password_expiry_days', '0')),
    }


def validate_password_policy(password):
    """
    Validate a password against the current system policy.

    Args:
        password (str): The password to validate.

    Returns:
        list: List of error message strings. Empty list if password is valid.
    """

    policy = get_password_policy()
    errors = []

    ## check minimum length
    if len(password) < policy['min_length']:
        errors.append('Password must be at least %d characters.' % policy['min_length'])

    ## check uppercase
    if policy['require_uppercase'] and not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter.')

    ## check lowercase
    if policy['require_lowercase'] and not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter.')

    ## check digit
    if policy['require_digit'] and not re.search(r'[0-9]', password):
        errors.append('Password must contain at least one digit.')

    ## check special character
    if policy['require_special'] and not re.search(r'[!@#$%^&*()\-_=+\[\]{}|;:\'",.<>?/\\`~]', password):
        errors.append('Password must contain at least one special character.')

    return errors


def get_password_policy_description():
    """
    Build a human-readable description of the current password policy.

    Returns:
        str: Description text for display in forms.
    """

    policy = get_password_policy()
    parts = ['Minimum %d characters' % policy['min_length']]

    if policy['require_uppercase']:
        parts.append('uppercase letter')
    if policy['require_lowercase']:
        parts.append('lowercase letter')
    if policy['require_digit']:
        parts.append('digit')
    if policy['require_special']:
        parts.append('special character')

    if len(parts) > 1:
        return '%s. Must include: %s.' % (parts[0], ', '.join(parts[1:]))
    return '%s.' % parts[0]
