"""
Accounts Views

Handles user, group, and role CRUD operations,
plus login/logout functionality.
"""

## import django pkgs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages

from .models import Role
from .forms import UserCreateForm, UserEditForm, GroupForm, RoleForm


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
            ip_address=request.META.get('REMOTE_ADDR')
        )
    except Exception:
        pass

    logout(request)
    return redirect('/accounts/login/')


## =============================================================
## User Management
## =============================================================

@login_required
def user_list(request):
    """List all users."""

    users = User.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {
        'nav_active': 'users',
        'users': users,
    })


@login_required
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


@login_required
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


@login_required
def user_toggle(request, user_id):
    """Toggle user active status (enable/disable)."""

    user_obj = get_object_or_404(User, pk=user_id)

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

@login_required
def group_list(request):
    """List all groups."""

    groups = Group.objects.all().order_by('name')
    return render(request, 'accounts/group_list.html', {
        'nav_active': 'groups',
        'groups': groups,
    })


@login_required
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
    })


@login_required
def group_edit(request, group_id):
    """Edit an existing group."""

    group_obj = get_object_or_404(Group, pk=group_id)

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group_obj)
        if form.is_valid():
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

    return render(request, 'accounts/group_form.html', {
        'nav_active': 'groups',
        'form': form,
        'form_title': 'Edit Group: %s' % group_obj.name,
    })


@login_required
def group_delete(request, group_id):
    """Delete a group."""

    group_obj = get_object_or_404(Group, pk=group_id)

    if request.method == 'POST':
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

@login_required
def role_list(request):
    """List all roles."""

    roles = Role.objects.all().order_by('name')
    return render(request, 'accounts/role_list.html', {
        'nav_active': 'roles',
        'roles': roles,
    })


@login_required
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
    })


@login_required
def role_edit(request, role_id):
    """Edit an existing role."""

    role_obj = get_object_or_404(Role, pk=role_id)

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role_obj)
        if form.is_valid():
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

    return render(request, 'accounts/role_form.html', {
        'nav_active': 'roles',
        'form': form,
        'form_title': 'Edit Role: %s' % role_obj.name,
    })


@login_required
def role_delete(request, role_id):
    """Delete a role."""

    role_obj = get_object_or_404(Role, pk=role_id)

    if request.method == 'POST':
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
