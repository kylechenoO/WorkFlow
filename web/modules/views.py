"""
Modules Views

Handles module listing, creation, editing, deletion,
and API endpoints for module introspection.
"""

## import buildin pkgs
import os
import re
import sys
import json
import time
import hashlib
from datetime import datetime

## import django pkgs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings

from accounts.decorators import require_permission
from workflows.models import WfVersion

## add lib/ to path for ModuleInspector
LIB_PATH = str(settings.PROJ_PATH / 'lib')
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

from ModuleInspector import ModuleInspector

## module root path
MOD_PATH = str(settings.PROJ_PATH / 'mod')

## core modules that cannot be deleted (all existing modules)
CORE_MODULES = {
    ('common', 'Bash'),
    ('common', 'Filter'),
    ('common', 'Http'),
    ('common', 'FileIO'),
    ('common', 'Notify'),
    ('common', 'Ssh'),
    ('common', 'MultiProcess'),
    ('common', 'DataTransformer'),
    ('common', 'Kt'),
    ('mysql', 'MySQL'),
    ('elasticsearchclient', 'ElasticSearch'),
    ('prometheus', 'Prometheus'),
}

## valid name pattern (alphanumeric + underscore, must start with uppercase for class)
NAME_PATTERN = re.compile(r'^[A-Z][A-Za-z0-9_]*$')
CATEGORY_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')

## module skeleton template
MODULE_TEMPLATE = '''"""
{class_name} Workflow Procedure Module

This module defines the {class_name} procedure class used by the workflow
engine. The class methods are invoked dynamically by the Flow engine
during workflow execution.
"""

## version related
__author__ = ""
__version__ = "0.0.2"
__email__ = ""

## import buildin pkgs


class {class_name}(object):
    """
    {class_name} workflow procedure.

    Responsibilities:
        - TODO: describe what this module does
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the {class_name} manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def example(self, context: dict, cfgs: dict) -> dict:
        """
        Example method — replace with your own.

        Args:
            param1 (str): Description of param1
            param2 (int): Optional description of param2 (default: 0)

        Returns:
            dict: Result with status key
        """

        ## load args
        param1 = cfgs.get('param1', '')

        ## debug prt
        self.logger.debug({{'param1': param1}})

        try:
            ## TODO: implement your logic here
            result = param1

            self.logger.info({{'status': '{class_name}.example completed'}})
            return {{
                'status': True,
                'data': result
            }}

        ## error handling
        except Exception as e:
            self.logger.error({{'status': 'Error in {class_name}.example: %s' % (e)}})
            return {{
                'status': False,
                'data': None
            }}
'''


def _get_inspector():
    """Create a ModuleInspector instance."""

    return ModuleInspector(MOD_PATH)


## human-readable descriptions for name patterns
PATTERN_HINTS = {
    CATEGORY_PATTERN: 'must start with a lowercase letter and contain only lowercase letters, digits, or underscores (e.g. "my_category")',
    NAME_PATTERN: 'must start with an uppercase letter and contain only letters, digits, or underscores (e.g. "MyModule")',
}


def _validate_name(name, pattern, label):
    """
    Validate a name against a pattern.

    Returns error message or None.
    """

    if not name:
        return '%s is required.' % label
    if not pattern.match(name):
        hint = PATTERN_HINTS.get(pattern, 'must match pattern: %s' % pattern.pattern)
        return '%s %s' % (label, hint)
    if len(name) > 64:
        return '%s must be 64 characters or less.' % label
    return None


## =============================================================
## Module Management Views
## =============================================================

@require_permission('modules', 'view')
def module_list(request):
    """List all workflow modules grouped by category."""

    inspector = _get_inspector()
    modules = inspector.list_modules()

    ## enrich with method names and details via introspection
    for mod in modules:
        try:
            info = inspector.inspect_module(mod['category'], mod['name'])
            if info and 'methods' in info:
                mod['method_count'] = len(info['methods'])
                mod['description'] = info.get('description', '')
                mod['methods'] = list(info['methods'].keys())
            else:
                mod['method_count'] = 0
                mod['description'] = ''
                mod['methods'] = []
        except Exception:
            mod['method_count'] = 0
            mod['description'] = ''
            mod['methods'] = []

        mod['is_core'] = (mod['category'], mod['name']) in CORE_MODULES

        ## format modified time
        try:
            mod['modified_str'] = datetime.fromtimestamp(mod['modified']).strftime('%Y-%m-%d %H:%M')
        except Exception:
            mod['modified_str'] = '-'

    ## sort modules by category then name
    modules.sort(key=lambda m: (m['category'], m['name']))

    ## auto-create v1 version snapshot for any module file discovered on the file system
    ## that has no version history yet (e.g. manually dropped files, restored from backup)
    for mod in modules:
        target_name = '%s.%s' % (mod['category'], mod['name'])
        try:
            if not WfVersion.objects.filter(type=WfVersion.TYPE_MODULE, target_name=target_name).exists():
                file_path = os.path.join(MOD_PATH, mod['category'], '%s.py' % mod['name'])
                with open(file_path, 'r', encoding='utf-8') as fh:
                    code = fh.read()
                WfVersion.create_version(
                    type=WfVersion.TYPE_MODULE,
                    target_name=target_name,
                    content=code,
                    changed_by='system',
                )
        except Exception:
            pass

    ## get available category dirs for create form
    cat_dirs = []
    try:
        for entry in sorted(os.listdir(MOD_PATH)):
            cat_path = os.path.join(MOD_PATH, entry)
            if os.path.isdir(cat_path) and not entry.startswith('_') and not entry.startswith('.'):
                cat_dirs.append(entry)
    except Exception:
        pass

    ## group modules by category (preserving order, including empty dirs)
    from collections import OrderedDict
    categories = OrderedDict()
    for cat in cat_dirs:
        categories[cat] = []
    for mod in modules:
        cat = mod['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(mod)

    return render(request, 'modules/module_list.html', {
        'nav_active': 'modules',
        'modules': modules,
        'categories': categories,
        'cat_dirs': cat_dirs,
        'total_modules': len(modules),
    })


@require_permission('modules', 'create')
def module_create(request):
    """Create a new module file."""

    if request.method == 'POST':
        category = request.POST.get('category', '').strip()
        module_name = request.POST.get('module_name', '').strip()
        new_category = request.POST.get('new_category', '').strip().lower()

        ## use new category if specified
        if new_category:
            category = new_category

        ## validate category
        err = _validate_name(category, CATEGORY_PATTERN, 'Category')
        if err:
            messages.error(request, err)
            return redirect('modules:module_list')

        ## validate module name
        err = _validate_name(module_name, NAME_PATTERN, 'Module name')
        if err:
            messages.error(request, err)
            return redirect('modules:module_list')

        ## check path safety
        cat_path = os.path.join(MOD_PATH, category)
        file_path = os.path.join(cat_path, '%s.py' % module_name)

        ## verify resolved path is within MOD_PATH
        real_file = os.path.realpath(file_path)
        real_mod = os.path.realpath(MOD_PATH)
        if not real_file.startswith(real_mod):
            messages.error(request, 'Invalid path.')
            return redirect('modules:module_list')

        ## check if already exists
        if os.path.exists(file_path):
            messages.error(request, 'Module "%s.%s" already exists.' % (category, module_name))
            return redirect('modules:module_list')

        ## create category dir if needed
        if not os.path.exists(cat_path):
            try:
                os.makedirs(cat_path, exist_ok=True)
            except Exception as e:
                messages.error(request, 'Failed to create category directory: %s' % e)
                return redirect('modules:module_list')

        ## write skeleton template
        try:
            content = MODULE_TEMPLATE.format(class_name=module_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            messages.error(request, 'Failed to create module file: %s' % e)
            return redirect('modules:module_list')

        ## save initial version
        try:
            WfVersion.create_version(
                type=WfVersion.TYPE_MODULE,
                target_name='%s.%s' % (category, module_name),
                content=content,
                changed_by=request.user.username,
            )
        except Exception:
            pass

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='create',
                target_type='module',
                target_name='%s.%s' % (category, module_name),
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Module "%s.%s" created successfully.' % (category, module_name))
        return redirect('modules:module_edit', category=category, module_name=module_name)

    return redirect('modules:module_list')


@require_permission('modules', 'edit')
def module_edit(request, category, module_name):
    """Edit a module file with CodeMirror Python editor."""

    ## validate inputs
    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    err = _validate_name(module_name, NAME_PATTERN, 'Module name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    ## build and verify path
    file_path = os.path.join(MOD_PATH, category, '%s.py' % module_name)
    real_file = os.path.realpath(file_path)
    real_mod = os.path.realpath(MOD_PATH)
    if not real_file.startswith(real_mod):
        messages.error(request, 'Invalid path.')
        return redirect('modules:module_list')

    if not os.path.isfile(file_path):
        messages.error(request, 'Module "%s.%s" not found.' % (category, module_name))
        return redirect('modules:module_list')

    ## handle save
    if request.method == 'POST':
        code = request.POST.get('code', '').replace('\r\n', '\n')

        ## read current code to check for changes
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_code = f.read()
        except Exception:
            current_code = None

        ## skip save if nothing changed
        if current_code is not None and current_code == code:
            messages.info(request, 'No changes detected.')
            return redirect('modules:module_edit', category=category, module_name=module_name)

        ## save current version BEFORE the write
        if current_code is not None:
            try:
                WfVersion.create_version(
                    type=WfVersion.TYPE_MODULE,
                    target_name='%s.%s' % (category, module_name),
                    content=current_code,
                    changed_by=request.user.username,
                )
            except Exception:
                pass

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            ## save new version AFTER the write so runlog can find it
            try:
                WfVersion.create_version(
                    type=WfVersion.TYPE_MODULE,
                    target_name='%s.%s' % (category, module_name),
                    content=code,
                    changed_by=request.user.username,
                )
            except Exception:
                pass

            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='module',
                    target_name='%s.%s' % (category, module_name),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass

            messages.success(request, 'Module saved successfully.')
        except Exception as e:
            messages.error(request, 'Failed to save module: %s' % e)

        return redirect('modules:module_edit', category=category, module_name=module_name)

    ## read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        messages.error(request, 'Failed to read module: %s' % e)
        code = ''

    ## introspect for side panel
    inspector = _get_inspector()
    mod_info = None
    try:
        mod_info = inspector.inspect_module(category, module_name)
    except Exception:
        pass

    is_core = (category, module_name) in CORE_MODULES

    return render(request, 'modules/module_edit.html', {
        'nav_active': 'modules',
        'category': category,
        'module_name': module_name,
        'code': code,
        'mod_info': mod_info,
        'mod_info_json': json.dumps(mod_info) if mod_info else '{}',
        'is_core': is_core,
    })


@require_permission('modules', 'delete')
def module_delete(request, category, module_name):
    """Delete a module file."""

    if request.method != 'POST':
        return redirect('modules:module_list')

    ## check if core module
    if (category, module_name) in CORE_MODULES:
        messages.error(request, 'Core module "%s.%s" cannot be deleted.' % (category, module_name))
        return redirect('modules:module_list')

    ## validate inputs
    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    err = _validate_name(module_name, NAME_PATTERN, 'Module name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    ## build and verify path
    file_path = os.path.join(MOD_PATH, category, '%s.py' % module_name)
    real_file = os.path.realpath(file_path)
    real_mod = os.path.realpath(MOD_PATH)
    if not real_file.startswith(real_mod):
        messages.error(request, 'Invalid path.')
        return redirect('modules:module_list')

    if not os.path.isfile(file_path):
        messages.error(request, 'Module "%s.%s" not found.' % (category, module_name))
        return redirect('modules:module_list')

    try:
        os.remove(file_path)

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='delete',
                target_type='module',
                target_name='%s.%s' % (category, module_name),
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Module "%s.%s" deleted.' % (category, module_name))
    except Exception as e:
        messages.error(request, 'Failed to delete module: %s' % e)

    return redirect('modules:module_list')


## =============================================================
## Category Management
## =============================================================

@require_permission('modules', 'create')
def category_create(request):
    """Create a new category directory."""

    if request.method != 'POST':
        return redirect('modules:module_list')

    cat_name = request.POST.get('category_name', '').strip().lower()

    err = _validate_name(cat_name, CATEGORY_PATTERN, 'Category name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    cat_path = os.path.join(MOD_PATH, cat_name)
    real_path = os.path.realpath(cat_path)
    real_mod = os.path.realpath(MOD_PATH)
    if not real_path.startswith(real_mod):
        messages.error(request, 'Invalid path.')
        return redirect('modules:module_list')

    if os.path.exists(cat_path):
        messages.error(request, 'Category "%s" already exists.' % cat_name)
        return redirect('modules:module_list')

    try:
        os.makedirs(cat_path, exist_ok=True)

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='create',
                target_type='category',
                target_name=cat_name,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Category "%s" created.' % cat_name)
    except Exception as e:
        messages.error(request, 'Failed to create category: %s' % e)

    return redirect('modules:module_list')


@require_permission('modules', 'edit')
def category_rename(request, category):
    """Rename a category directory."""

    if request.method != 'POST':
        return redirect('modules:module_list')

    new_name = request.POST.get('new_name', '').strip().lower()

    ## validate old name
    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    ## validate new name
    err = _validate_name(new_name, CATEGORY_PATTERN, 'New category name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    old_path = os.path.join(MOD_PATH, category)
    new_path = os.path.join(MOD_PATH, new_name)

    ## verify paths
    real_old = os.path.realpath(old_path)
    real_new = os.path.realpath(new_path)
    real_mod = os.path.realpath(MOD_PATH)
    if not real_old.startswith(real_mod) or not real_new.startswith(real_mod):
        messages.error(request, 'Invalid path.')
        return redirect('modules:module_list')

    if not os.path.isdir(old_path):
        messages.error(request, 'Category "%s" not found.' % category)
        return redirect('modules:module_list')

    if os.path.exists(new_path):
        messages.error(request, 'Category "%s" already exists.' % new_name)
        return redirect('modules:module_list')

    ## check if any core modules in this category
    has_core = any(cat == category for cat, _ in CORE_MODULES)
    if has_core:
        messages.error(request, 'Cannot rename category "%s" — contains core modules.' % category)
        return redirect('modules:module_list')

    try:
        os.rename(old_path, new_path)

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='rename',
                target_type='category',
                target_name='%s → %s' % (category, new_name),
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Category renamed from "%s" to "%s".' % (category, new_name))
    except Exception as e:
        messages.error(request, 'Failed to rename category: %s' % e)

    return redirect('modules:module_list')


@require_permission('modules', 'delete')
def category_delete(request, category):
    """Delete an empty category directory."""

    if request.method != 'POST':
        return redirect('modules:module_list')

    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    cat_path = os.path.join(MOD_PATH, category)
    real_path = os.path.realpath(cat_path)
    real_mod = os.path.realpath(MOD_PATH)
    if not real_path.startswith(real_mod):
        messages.error(request, 'Invalid path.')
        return redirect('modules:module_list')

    if not os.path.isdir(cat_path):
        messages.error(request, 'Category "%s" not found.' % category)
        return redirect('modules:module_list')

    ## check if any core modules in this category
    has_core = any(cat == category for cat, _ in CORE_MODULES)
    if has_core:
        messages.error(request, 'Cannot delete category "%s" — contains core modules.' % category)
        return redirect('modules:module_list')

    ## check if directory has any .py files
    py_files = [f for f in os.listdir(cat_path) if f.endswith('.py') and not f.startswith('_') and ' ' not in f]
    if py_files:
        messages.error(request, 'Cannot delete category "%s" — still contains %d module(s). Delete all modules first.' % (category, len(py_files)))
        return redirect('modules:module_list')

    try:
        import shutil
        shutil.rmtree(cat_path)

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='delete',
                target_type='category',
                target_name=category,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception:
            pass

        messages.success(request, 'Category "%s" deleted.' % category)
    except Exception as e:
        messages.error(request, 'Failed to delete category: %s' % e)

    return redirect('modules:module_list')


## =============================================================
## Version History Views
## =============================================================

@require_permission('modules', 'view')
def module_versions(request, category, module_name):
    """Show version history for a module."""

    ## validate inputs
    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    err = _validate_name(module_name, NAME_PATTERN, 'Module name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    target_name = '%s.%s' % (category, module_name)
    versions = WfVersion.get_history(WfVersion.TYPE_MODULE, target_name)

    return render(request, 'modules/module_versions.html', {
        'nav_active': 'modules',
        'category': category,
        'module_name': module_name,
        'target_name': target_name,
        'versions': versions,
    })


@require_permission('modules', 'view')
def module_version_detail(request, category, module_name, version_id):
    """Show a specific module version's content."""

    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    err = _validate_name(module_name, NAME_PATTERN, 'Module name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    target_name = '%s.%s' % (category, module_name)
    version = get_object_or_404(
        WfVersion, pk=version_id,
        type=WfVersion.TYPE_MODULE,
        target_name=target_name,
    )

    return render(request, 'modules/module_version_detail.html', {
        'nav_active': 'modules',
        'category': category,
        'module_name': module_name,
        'version': version,
        'content': version.content,
    })


@require_permission('modules', 'view')
def module_version_diff(request, category, module_name):
    """Compare two module versions side by side."""

    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    err = _validate_name(module_name, NAME_PATTERN, 'Module name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    target_name = '%s.%s' % (category, module_name)

    v1_id = request.GET.get('v1')
    v2_id = request.GET.get('v2')

    v1 = get_object_or_404(
        WfVersion, pk=v1_id,
        type=WfVersion.TYPE_MODULE,
        target_name=target_name,
    )
    v2 = get_object_or_404(
        WfVersion, pk=v2_id,
        type=WfVersion.TYPE_MODULE,
        target_name=target_name,
    )

    return render(request, 'modules/module_version_diff.html', {
        'nav_active': 'modules',
        'category': category,
        'module_name': module_name,
        'v1': v1,
        'v2': v2,
    })


@require_permission('modules', 'edit')
def module_version_restore(request, category, module_name, version_id):
    """Restore a module to a previous version."""

    if request.method != 'POST':
        return redirect('modules:module_versions', category=category, module_name=module_name)

    ## validate inputs
    err = _validate_name(category, CATEGORY_PATTERN, 'Category')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    err = _validate_name(module_name, NAME_PATTERN, 'Module name')
    if err:
        messages.error(request, err)
        return redirect('modules:module_list')

    ## build and verify path
    file_path = os.path.join(MOD_PATH, category, '%s.py' % module_name)
    real_file = os.path.realpath(file_path)
    real_mod = os.path.realpath(MOD_PATH)
    if not real_file.startswith(real_mod):
        messages.error(request, 'Invalid path.')
        return redirect('modules:module_list')

    target_name = '%s.%s' % (category, module_name)
    version = get_object_or_404(
        WfVersion, pk=version_id,
        type=WfVersion.TYPE_MODULE,
        target_name=target_name,
    )

    ## save current state before restoring
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_code = f.read()
        WfVersion.create_version(
            type=WfVersion.TYPE_MODULE,
            target_name=target_name,
            content=current_code,
            changed_by=request.user.username,
        )
    except Exception:
        pass

    ## write restored content to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(version.content)

        ## save restored version AFTER the write so version history is current
        try:
            WfVersion.create_version(
                type=WfVersion.TYPE_MODULE,
                target_name=target_name,
                content=version.content,
                changed_by=request.user.username,
            )
        except Exception:
            pass

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='restore',
                target_type='module',
                target_name=target_name,
                detail={'restored_version': version.version},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        messages.success(request, 'Module "%s" restored to version %d.' % (target_name, version.version))
    except Exception as e:
        messages.error(request, 'Failed to restore module: %s' % e)

    return redirect('modules:module_versions', category=category, module_name=module_name)


## =============================================================
## API Endpoints
## =============================================================

@require_permission('modules', 'view')
def api_registry(request):
    """API: Return full module registry as JSON for Visual Editor."""

    inspector = _get_inspector()
    registry = inspector.scan_all()
    return JsonResponse(registry)


@require_permission('modules', 'view')
def api_introspect(request, category, module_name):
    """API: Return introspection data for a single module."""

    inspector = _get_inspector()
    mod_info = inspector.inspect_module(category, module_name)

    if mod_info is None:
        return JsonResponse({'error': 'Module not found'}, status=404)

    return JsonResponse(mod_info)
