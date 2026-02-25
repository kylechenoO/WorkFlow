"""
Accounts Views

Handles user, group, and role CRUD operations,
plus login/logout functionality.
"""

## import django pkgs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.core.paginator import Paginator

from .models import Role, Permission, GroupPermission
from .forms import UserCreateForm, UserEditForm, GroupForm, RoleForm, ProfileForm
from accounts.decorators import require_permission
from collections import OrderedDict

## default groups and roles that cannot be deleted
PROTECTED_NAMES = {'admin', 'user'}


def _get_permission_groups():
    """Build ordered dict of permissions grouped by page for template rendering."""

    perms = Permission.objects.all().order_by('page', 'action')
    groups = OrderedDict()
    for p in perms:
        if p.page not in groups:
            groups[p.page] = []
        groups[p.page].append(p)
    return groups


## =============================================================
## Authentication
## =============================================================

def login_view(request):
    """Handle user login."""

    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=user,
                    action='login',
                    target_type='user',
                    target_name=user.username,
                    detail={
                        'request': {
                            'method': 'POST',
                            'path': '/accounts/login/',
                            'body': {'username': username},
                        },
                        'response': {'status_code': 302, 'redirect': '/'}
                    },
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            return redirect('/')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Handle user logout."""

    ## log audit
    try:
        from audit.models import AuditLog
        AuditLog.log(
            user=request.user,
            action='logout',
            target_type='user',
            target_name=request.user.username,
            detail={
                'request': {'method': 'GET', 'path': '/accounts/logout/'},
                'response': {'status_code': 302, 'redirect': '/accounts/login/'}
            },
            ip_address=request.META.get('REMOTE_ADDR')
        )
    except Exception:
        pass

    logout(request)
    return redirect('/accounts/login/')


@login_required
def change_password(request):
    """Handle user password change."""

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            ## validate against password policy
            from accounts.password_policy import validate_password_policy
            policy_errors = validate_password_policy(new_password)
            if policy_errors:
                for err in policy_errors:
                    messages.error(request, err)
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)

                ## update password_changed_at
                try:
                    from accounts.models import UserProfile
                    from django.utils import timezone as dj_tz
                    profile, _ = UserProfile.objects.get_or_create(user=request.user)
                    profile.password_changed_at = dj_tz.now()
                    profile.save(update_fields=['password_changed_at'])
                except Exception:
                    pass

                ## log audit
                try:
                    from audit.models import AuditLog
                    AuditLog.log(
                        user=request.user,
                        action='update',
                        target_type='user',
                        target_name=request.user.username,
                        detail={'field': 'password'},
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                except Exception:
                    pass

                messages.success(request, 'Password changed successfully.')
                return redirect('/')

    from accounts.password_policy import get_password_policy_description
    return render(request, 'accounts/change_password.html', {
        'nav_active': '',
        'password_policy_desc': get_password_policy_description(),
    })


## =============================================================
## User Profile
## =============================================================

@login_required
def profile(request):
    """User profile page — edit personal info and change password."""

    profile_saved = False
    password_changed = False

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_profile':
            form = ProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()

                ## log audit
                try:
                    from audit.models import AuditLog
                    AuditLog.log(
                        user=request.user,
                        action='update',
                        target_type='user',
                        target_name=request.user.username,
                        detail={'field': 'profile'},
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                except Exception:
                    pass

                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:profile')

        elif action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            else:
                ## validate against password policy
                from accounts.password_policy import validate_password_policy
                policy_errors = validate_password_policy(new_password)
                if policy_errors:
                    for err in policy_errors:
                        messages.error(request, err)
                else:
                    request.user.set_password(new_password)
                    request.user.save()
                    update_session_auth_hash(request, request.user)

                    ## update password_changed_at
                    try:
                        from accounts.models import UserProfile
                        from django.utils import timezone as dj_tz
                        profile, _ = UserProfile.objects.get_or_create(user=request.user)
                        profile.password_changed_at = dj_tz.now()
                        profile.save(update_fields=['password_changed_at'])
                    except Exception:
                        pass

                    ## log audit
                    try:
                        from audit.models import AuditLog
                        AuditLog.log(
                            user=request.user,
                            action='update',
                            target_type='user',
                            target_name=request.user.username,
                            detail={'field': 'password'},
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    except Exception:
                        pass

                    messages.success(request, 'Password changed successfully.')
                    return redirect('accounts:profile')

    form = ProfileForm(instance=request.user)

    ## get user groups and roles for display
    user_groups = request.user.groups.all()
    user_roles = request.user.wf_roles.all()

    from accounts.password_policy import get_password_policy_description
    return render(request, 'accounts/profile.html', {
        'nav_active': '',
        'form': form,
        'user_groups': user_groups,
        'user_roles': user_roles,
        'password_policy_desc': get_password_policy_description(),
    })


## =============================================================
## User Management
## =============================================================

@require_permission('users', 'view')
def user_list(request):
    """List all users."""

    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    users_qs = User.objects.all().order_by('username')
    paginator = Paginator(users_qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/user_list.html', {
        'nav_active': 'system',
        'users': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
    })


@require_permission('users', 'create')
def user_create(request):
    """Create a new user."""

    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='create',
                    target_type='user',
                    target_name=user.username,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'User "%s" created successfully.' % user.username)
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm()

    return render(request, 'accounts/user_form.html', {
        'nav_active': 'users',
        'form': form,
        'form_title': 'Create User',
    })


@require_permission('users', 'edit')
def user_edit(request, user_id):
    """Edit an existing user."""

    user_obj = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save()

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='user',
                    target_name=user.username,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'User "%s" updated successfully.' % user.username)
            return redirect('accounts:user_list')
    else:
        form = UserEditForm(instance=user_obj)

    return render(request, 'accounts/user_form.html', {
        'nav_active': 'users',
        'form': form,
        'form_title': 'Edit User: %s' % user_obj.username,
    })


@require_permission('users', 'toggle')
def user_toggle(request, user_id):
    """Toggle user active status (enable/disable)."""

    user_obj = get_object_or_404(User, pk=user_id)

    ## prevent disabling the default admin account
    if user_obj.username == 'admin':
        messages.error(request, 'The default admin account cannot be disabled.')
        return redirect('accounts:user_list')

    if request.method == 'POST':
        user_obj.is_active = not user_obj.is_active
        user_obj.save()

        action = 'enable' if user_obj.is_active else 'disable'

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action=action,
                target_type='user',
                target_name=user_obj.username,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'User "%s" %sd.' % (user_obj.username, action))

    return redirect('accounts:user_list')


## =============================================================
## Group Management
## =============================================================

@require_permission('groups', 'view')
def group_list(request):
    """List all groups."""

    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    groups_qs = Group.objects.all().order_by('name')
    paginator = Paginator(groups_qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/group_list.html', {
        'nav_active': 'system',
        'groups': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
        'protected_names': PROTECTED_NAMES,
    })


@require_permission('groups', 'create')
def group_create(request):
    """Create a new group."""

    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='create',
                    target_type='group',
                    target_name=group.name,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'Group "%s" created successfully.' % group.name)
            return redirect('accounts:group_list')
    else:
        form = GroupForm()

    return render(request, 'accounts/group_form.html', {
        'nav_active': 'groups',
        'form': form,
        'form_title': 'Create Group',
        'permission_groups': _get_permission_groups(),
        'selected_perm_ids': [],
    })


@require_permission('groups', 'edit')
def group_edit(request, group_id):
    """Edit an existing group."""

    group_obj = get_object_or_404(Group, pk=group_id)
    is_protected = group_obj.name in PROTECTED_NAMES

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group_obj)
        if form.is_valid():
            ## protect default group name from rename
            if is_protected:
                new_name = form.cleaned_data.get('name', '')
                if new_name != group_obj.name:
                    messages.error(request, 'Default group "%s" cannot be renamed.' % group_obj.name)
                    return redirect('accounts:group_list')

            group = form.save()

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='group',
                    target_name=group.name,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'Group "%s" updated successfully.' % group.name)
            return redirect('accounts:group_list')
    else:
        form = GroupForm(instance=group_obj)

    ## get selected permission IDs for template
    selected_perm_ids = list(
        GroupPermission.objects.filter(group=group_obj).values_list('permission_id', flat=True)
    )

    return render(request, 'accounts/group_form.html', {
        'nav_active': 'groups',
        'form': form,
        'form_title': 'Edit Group: %s' % group_obj.name,
        'is_protected': is_protected,
        'permission_groups': _get_permission_groups(),
        'selected_perm_ids': selected_perm_ids,
    })


@require_permission('groups', 'delete')
def group_delete(request, group_id):
    """Delete a group."""

    group_obj = get_object_or_404(Group, pk=group_id)

    if request.method == 'POST':
        ## protect default groups
        if group_obj.name in PROTECTED_NAMES:
            messages.error(request, 'Default group "%s" cannot be deleted.' % group_obj.name)
            return redirect('accounts:group_list')

        name = group_obj.name
        group_obj.delete()

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='delete',
                target_type='group',
                target_name=name,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Group "%s" deleted.' % name)

    return redirect('accounts:group_list')


## =============================================================
## Role Management
## =============================================================

@require_permission('roles', 'view')
def role_list(request):
    """List all roles."""

    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    roles_qs = Role.objects.all().order_by('name')
    paginator = Paginator(roles_qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/role_list.html', {
        'nav_active': 'system',
        'roles': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
        'protected_names': PROTECTED_NAMES,
    })


@require_permission('roles', 'create')
def role_create(request):
    """Create a new role."""

    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='create',
                    target_type='role',
                    target_name=role.name,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'Role "%s" created successfully.' % role.name)
            return redirect('accounts:role_list')
    else:
        form = RoleForm()

    return render(request, 'accounts/role_form.html', {
        'nav_active': 'roles',
        'form': form,
        'form_title': 'Create Role',
        'permission_groups': _get_permission_groups(),
        'selected_perm_ids': [],
    })


@require_permission('roles', 'edit')
def role_edit(request, role_id):
    """Edit an existing role."""

    role_obj = get_object_or_404(Role, pk=role_id)
    is_protected = role_obj.name in PROTECTED_NAMES

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role_obj)
        if form.is_valid():
            ## protect default role name from rename
            if is_protected:
                new_name = form.cleaned_data.get('name', '')
                if new_name != role_obj.name:
                    messages.error(request, 'Default role "%s" cannot be renamed.' % role_obj.name)
                    return redirect('accounts:role_list')

            role = form.save()

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='role',
                    target_name=role.name,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'Role "%s" updated successfully.' % role.name)
            return redirect('accounts:role_list')
    else:
        form = RoleForm(instance=role_obj)

    ## get selected permission IDs for template
    selected_perm_ids = list(role_obj.permissions.values_list('id', flat=True))

    return render(request, 'accounts/role_form.html', {
        'nav_active': 'roles',
        'form': form,
        'form_title': 'Edit Role: %s' % role_obj.name,
        'is_protected': is_protected,
        'permission_groups': _get_permission_groups(),
        'selected_perm_ids': selected_perm_ids,
    })


@require_permission('roles', 'delete')
def role_delete(request, role_id):
    """Delete a role."""

    role_obj = get_object_or_404(Role, pk=role_id)

    if request.method == 'POST':
        ## protect default roles
        if role_obj.name in PROTECTED_NAMES:
            messages.error(request, 'Default role "%s" cannot be deleted.' % role_obj.name)
            return redirect('accounts:role_list')

        name = role_obj.name
        role_obj.delete()

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='delete',
                target_type='role',
                target_name=name,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Role "%s" deleted.' % name)

    return redirect('accounts:role_list')
