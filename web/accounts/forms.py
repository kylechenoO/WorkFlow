"""
Accounts Forms

Forms for user, group, and role management.
"""

## import django pkgs
from django import forms
from django.contrib.auth.models import User, Group
from .models import Role, Permission, GroupPermission


class UserCreateForm(forms.ModelForm):
    """Form for creating a new user with group/role assignment."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Minimum 8 characters.'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm Password'
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Groups'
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Roles'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ## pre-select default 'user' group and role for new users
        try:
            default_group = Group.objects.filter(name='user')
            self.fields['groups'].initial = default_group
        except Group.DoesNotExist:
            pass
        try:
            default_role = Role.objects.filter(name='user')
            self.fields['roles'].initial = default_role
        except Role.DoesNotExist:
            pass
        ## dynamic password help text from policy
        try:
            from accounts.password_policy import get_password_policy_description
            self.fields['password'].help_text = get_password_policy_description()
        except Exception:
            pass

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')
        elif password:
            ## validate against password policy
            from accounts.password_policy import validate_password_policy
            for err in validate_password_policy(password):
                self.add_error('password', err)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            ## save M2M for groups
            self.save_m2m()
            ## save roles (custom M2M via Role.users)
            selected_roles = self.cleaned_data.get('roles', [])
            for role in Role.objects.all():
                if role in selected_roles:
                    role.users.add(user)
                else:
                    role.users.remove(user)
            ## set initial password_changed_at
            try:
                from accounts.models import UserProfile
                from django.utils import timezone as dj_tz
                UserProfile.objects.get_or_create(user=user, defaults={'password_changed_at': dj_tz.now()})
            except Exception:
                pass
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing an existing user with group/role assignment."""

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Leave blank to keep current password.'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label='Confirm Password'
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Groups'
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Roles'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ## pre-select current groups/roles if editing
        if self.instance and self.instance.pk:
            self.fields['groups'].initial = self.instance.groups.all()
            self.fields['roles'].initial = self.instance.wf_roles.all()
        ## dynamic password help text from policy
        try:
            from accounts.password_policy import get_password_policy_description
            self.fields['password'].help_text = 'Leave blank to keep current password. %s' % get_password_policy_description()
        except Exception:
            pass

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password != password_confirm:
            self.add_error('password_confirm', 'Passwords do not match.')
        elif password:
            ## validate against password policy
            from accounts.password_policy import validate_password_policy
            for err in validate_password_policy(password):
                self.add_error('password', err)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            ## save M2M for groups
            self.save_m2m()
            ## save roles (custom M2M via Role.users)
            selected_roles = self.cleaned_data.get('roles', [])
            for role in Role.objects.all():
                if role in selected_roles:
                    role.users.add(user)
                else:
                    role.users.remove(user)
            ## update password_changed_at if password was changed
            if password:
                try:
                    from accounts.models import UserProfile
                    from django.utils import timezone as dj_tz
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.password_changed_at = dj_tz.now()
                    profile.save(update_fields=['password_changed_at'])
                except Exception:
                    pass
        return user


class ProfileForm(forms.ModelForm):
    """Form for users to edit their own profile info."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class GroupForm(forms.ModelForm):
    """Form for creating/editing a group with permission assignment."""

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('page', 'action'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Permissions'
    )

    class Meta:
        model = Group
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ## pre-select current permissions if editing
        if self.instance and self.instance.pk:
            current_perm_ids = GroupPermission.objects.filter(
                group=self.instance
            ).values_list('permission_id', flat=True)
            self.fields['permissions'].initial = Permission.objects.filter(id__in=current_perm_ids)

    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit and group.pk:
            ## update group permissions
            selected = self.cleaned_data.get('permissions', [])
            ## remove old
            GroupPermission.objects.filter(group=group).exclude(
                permission__in=selected
            ).delete()
            ## add new
            for perm in selected:
                GroupPermission.objects.get_or_create(group=group, permission=perm)
        return group


class RoleForm(forms.ModelForm):
    """Form for creating/editing a role with permission assignment."""

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('page', 'action'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Permissions'
    )

    class Meta:
        model = Role
        fields = ['name', 'description', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
