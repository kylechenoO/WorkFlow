"""
System Views

Provides system configuration pages (timezone, version, etc.).
"""

## import buildin pkgs
import re
import io
import os
import json
import json5
import time
import signal
import zipfile
import hashlib
import zoneinfo
import subprocess

## import 3rd party pkgs
import requests as http_requests

## import django pkgs
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import connection

from accounts.decorators import require_permission
from system.models import SystemSetting, DevtoolRequest, ApiKey

## add lib/ to path for ModuleInspector
import sys
_LIB_PATH = str(settings.PROJ_PATH / 'lib')
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)
from ModuleInspector import ModuleInspector

_MOD_PATH = str(settings.PROJ_PATH / 'mod')


## =============================================================
## Timezone Choices — curated list grouped by region
## =============================================================

TIMEZONE_CHOICES = [
    ('UTC', [
        'UTC',
    ]),
    ('US', [
        'US/Eastern',
        'US/Central',
        'US/Mountain',
        'US/Pacific',
        'US/Alaska',
        'US/Hawaii',
    ]),
    ('Europe', [
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Europe/Madrid',
        'Europe/Rome',
        'Europe/Amsterdam',
        'Europe/Brussels',
        'Europe/Zurich',
        'Europe/Vienna',
        'Europe/Stockholm',
        'Europe/Oslo',
        'Europe/Helsinki',
        'Europe/Warsaw',
        'Europe/Prague',
        'Europe/Budapest',
        'Europe/Bucharest',
        'Europe/Athens',
        'Europe/Istanbul',
        'Europe/Moscow',
        'Europe/Kiev',
    ]),
    ('Asia', [
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Hong_Kong',
        'Asia/Taipei',
        'Asia/Seoul',
        'Asia/Singapore',
        'Asia/Kolkata',
        'Asia/Mumbai',
        'Asia/Dubai',
        'Asia/Bangkok',
        'Asia/Jakarta',
        'Asia/Kuala_Lumpur',
        'Asia/Manila',
        'Asia/Ho_Chi_Minh',
        'Asia/Karachi',
        'Asia/Dhaka',
        'Asia/Colombo',
        'Asia/Riyadh',
        'Asia/Tehran',
        'Asia/Baghdad',
        'Asia/Beirut',
        'Asia/Jerusalem',
    ]),
    ('Australia / Pacific', [
        'Australia/Sydney',
        'Australia/Melbourne',
        'Australia/Brisbane',
        'Australia/Perth',
        'Australia/Adelaide',
        'Australia/Hobart',
        'Pacific/Auckland',
        'Pacific/Fiji',
        'Pacific/Guam',
        'Pacific/Honolulu',
    ]),
    ('Americas', [
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
        'America/Anchorage',
        'America/Toronto',
        'America/Vancouver',
        'America/Mexico_City',
        'America/Bogota',
        'America/Lima',
        'America/Santiago',
        'America/Buenos_Aires',
        'America/Sao_Paulo',
        'America/Caracas',
    ]),
    ('Africa', [
        'Africa/Cairo',
        'Africa/Johannesburg',
        'Africa/Lagos',
        'Africa/Nairobi',
        'Africa/Casablanca',
        'Africa/Addis_Ababa',
    ]),
]

## build flat set for validation
VALID_TIMEZONES = set()
for _group, _zones in TIMEZONE_CHOICES:
    for tz in _zones:
        VALID_TIMEZONES.add(tz)


## =============================================================
## Views
## =============================================================

@require_permission('system', 'edit')
def timezone_view(request):
    """
    System timezone settings page.

    GET:  show current timezone and dropdown to change it.
    POST: validate and save the new timezone.
    """

    if request.method == 'POST':
        new_tz = request.POST.get('timezone', '').strip()

        ## validate
        if new_tz not in VALID_TIMEZONES:
            messages.error(request, 'Invalid timezone: %s' % new_tz)
            return redirect('system:timezone')

        ## save
        try:
            old_tz = SystemSetting.get('timezone', 'UTC')
            SystemSetting.set('timezone', new_tz)

            ## clear middleware cache
            from system.middleware import _clear_cache
            _clear_cache()

            ## audit log
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='system_setting',
                    target_name='timezone',
                    detail='Changed timezone from %s to %s' % (old_tz, new_tz),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Timezone updated to %s' % new_tz)
        except Exception as e:
            messages.error(request, 'Failed to save timezone: %s' % e)

        return redirect('system:timezone')

    ## GET
    current_tz = SystemSetting.get('timezone', 'UTC')

    ## get current time in the selected timezone
    from django.utils import timezone as django_tz
    try:
        tz_info = zoneinfo.ZoneInfo(current_tz)
        now = django_tz.now().astimezone(tz_info)
        current_time = now.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception:
        current_time = 'Unable to determine'

    return render(request, 'system/timezone.html', {
        'nav_active': 'system',
        'timezone_choices': TIMEZONE_CHOICES,
        'current_tz': current_tz,
        'current_time': current_time,
    })


## =============================================================
## Version View
## =============================================================

def _read_pyproject_meta():
    """
    Read name, version, author, email from pyproject.toml.

    Returns:
        dict: { 'name', 'version', 'author', 'email' }
    """

    meta = {'name': 'WorkFlow', 'version': '', 'author': '', 'email': ''}
    try:
        toml_path = settings.PROJ_PATH / 'pyproject.toml'
        with open(toml_path, 'r', encoding='utf-8') as f:
            content = f.read()

        ## name
        m = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if m:
            meta['name'] = m.group(1).strip()

        ## version
        m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if m:
            meta['version'] = m.group(1).strip()

        ## authors = [{ name = "...", email = "..." }]
        m = re.search(r'authors\s*=\s*\[.*?name\s*=\s*["\']([^"\']*)["\']', content, re.DOTALL)
        if m:
            meta['author'] = m.group(1).strip()

        m = re.search(r'authors\s*=\s*\[.*?email\s*=\s*["\']([^"\']*)["\']', content, re.DOTALL)
        if m:
            meta['email'] = m.group(1).strip()

    except Exception:
        pass
    return meta


@require_permission('system', 'edit')
def version_view(request):
    """
    System version info page.

    Displays WorkFlow application name, version, author and email
    read from pyproject.toml.
    """

    info = _read_pyproject_meta()

    return render(request, 'system/version.html', {
        'nav_active': 'system',
        'app_name': info['name'],
        'app_version': info['version'],
        'app_author': info['author'],
        'app_email': info['email'],
    })


@require_permission('system', 'edit')
def license_view(request):
    """
    System license page — displays the content of the LICENSE file.
    """

    license_text = ''
    try:
        license_path = settings.PROJ_PATH / 'LICENSE'
        license_text = license_path.read_text(encoding='utf-8')
    except Exception:
        pass

    return render(request, 'system/license.html', {
        'nav_active': 'system',
        'license_text': license_text,
    })


## =============================================================
## Devtool Views
## =============================================================

## SQL statements that are not allowed in SQLtool
_SQL_BLOCKED = {'DROP', 'TRUNCATE', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'REPLACE'}


@require_permission('devtool', 'use')
def devtool_view(request):
    """
    Devtool page — RESTFultool and SQLtool sub-tabs.
    """

    return render(request, 'system/devtool.html', {
        'nav_active': 'devtool',
    })


@require_permission('devtool', 'use')
@require_POST
def devtool_request(request):
    """
    AJAX endpoint — execute an HTTP request and persist history.

    Accepts JSON body: { method, url, headers (JSON string or object), body }
    Returns JSON: { status, status_code, response_text, duration_ms, id }
    """

    ## load args
    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': False, 'error': 'Invalid JSON body'}, status=400)

    method  = payload.get('method', 'GET').upper()
    url     = payload.get('url', '').strip()
    headers = payload.get('headers', '')
    body    = payload.get('body', '')

    ## validate
    if not url:
        return JsonResponse({'status': False, 'error': 'URL is required'}, status=400)

    if method not in {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}:
        return JsonResponse({'status': False, 'error': 'Unsupported HTTP method'}, status=400)

    ## parse headers
    parsed_headers = {}
    if headers:
        if isinstance(headers, str):
            try:
                parsed_headers = json.loads(headers)
            except Exception:
                return JsonResponse({'status': False, 'error': 'Headers must be valid JSON'}, status=400)
        elif isinstance(headers, dict):
            parsed_headers = headers

    ## try:
    try:
        t0 = time.time()
        resp = http_requests.request(
            method=method,
            url=url,
            headers=parsed_headers,
            data=body.encode('utf-8') if body else None,
            timeout=30,
            verify=True,
            allow_redirects=True,
        )
        duration_ms = int((time.time() - t0) * 1000)

        ## truncate response to 50KB for storage
        response_text = resp.text[:51200] if resp.text else ''

        ## persist history
        entry = DevtoolRequest.objects.create(
            user=request.user.username,
            method=method,
            url=url,
            headers=parsed_headers,
            body=body,
            status_code=resp.status_code,
            response=response_text,
            duration_ms=duration_ms,
        )

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='request',
                target_type='devtool',
                target_name=url,
                detail={
                    'request': {'method': method, 'url': url},
                    'response': {'status_code': resp.status_code, 'duration_ms': duration_ms},
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return JsonResponse({
            'status': True,
            'id': entry.id,
            'status_code': resp.status_code,
            'response_text': response_text,
            'duration_ms': duration_ms,
        })

    ## error handling
    except http_requests.exceptions.ConnectionError as e:
        return JsonResponse({'status': False, 'error': 'Connection error: %s' % str(e)[:200]})
    except http_requests.exceptions.Timeout:
        return JsonResponse({'status': False, 'error': 'Request timed out (30s)'})
    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)[:200]})


@require_permission('devtool', 'use')
@require_POST
def devtool_sql(request):
    """
    AJAX endpoint — execute a read-only SQL query against the WorkFlow DB.

    Only SELECT, SHOW, DESCRIBE statements are permitted.
    Results are capped at 500 rows.

    Accepts JSON body: { sql }
    Returns JSON: { status, columns, rows, row_count, duration_ms }
    """

    ## load args
    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': False, 'error': 'Invalid JSON body'}, status=400)

    sql = payload.get('sql', '').strip()

    if not sql:
        return JsonResponse({'status': False, 'error': 'SQL is required'}, status=400)

    ## security — block destructive statements
    first_token = sql.split()[0].upper() if sql.split() else ''
    if first_token in _SQL_BLOCKED:
        return JsonResponse({
            'status': False,
            'error': 'Statement not allowed: %s. Only SELECT, SHOW, DESCRIBE are permitted.' % first_token,
        })

    ## try:
    try:
        t0 = time.time()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            duration_ms = int((time.time() - t0) * 1000)

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(500)
                ## convert non-serialisable types to str
                safe_rows = []
                for row in rows:
                    safe_rows.append([str(v) if v is not None and not isinstance(v, (int, float, bool, str)) else v for v in row])

                ## audit log
                try:
                    from audit.models import AuditLog
                    AuditLog.log(
                        user=request.user,
                        action='query',
                        target_type='devtool',
                        target_name='sqltool',
                        detail={
                            'request': {'method': 'SQL', 'body': {'sql': sql}},
                            'response': {'status_code': 200, 'row_count': len(safe_rows), 'duration_ms': duration_ms},
                        },
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                except Exception:
                    pass

                return JsonResponse({
                    'status': True,
                    'columns': columns,
                    'rows': safe_rows,
                    'row_count': len(safe_rows),
                    'duration_ms': duration_ms,
                })
            else:
                return JsonResponse({
                    'status': True,
                    'columns': [],
                    'rows': [],
                    'row_count': 0,
                    'duration_ms': duration_ms,
                })

    ## error handling
    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)})


## =============================================================
## APIs Page Views
## =============================================================

@require_permission('system', 'edit')
def apis_view(request):
    """
    APIs page — Token Management tab (default) + API & Modules tab
    with dynamic Module Reference generated from ModuleInspector.
    """

    keys = ApiKey.objects.all()

    ## pop plain key from session — shown once after creation
    new_api_key = request.session.pop('new_api_key', None)

    ## scan all modules for Module Reference section
    modules_registry = {}
    try:
        inspector = ModuleInspector(_MOD_PATH)
        modules_registry = inspector.scan_all()
        ## post-process for Django template compatibility
        for _cat_data in modules_registry.values():
            for _mod_data in _cat_data.get('modules', {}).values():
                methods = _mod_data.get('methods', {})
                ## Django templates can't do dict.keys()|first
                _mod_data['first_method'] = next(iter(methods)) if methods else ''
                ## add default_display string for params (Django can't distinguish None/False/0)
                ## also remap 'ref' type to real data type for API docs display
                for _method_data in methods.values():
                    for _p_data in _method_data.get('params', {}).values():
                        if 'default' in _p_data:
                            _p_data['default_display'] = json.dumps(_p_data['default'])
                        if _p_data.get('type') == 'ref':
                            _p_data['type'] = 'list | dict'
    except Exception:
        pass

    return render(request, 'system/apis.html', {
        'nav_active': 'apis',
        'keys': keys,
        'active_tab': 'tokens',
        'new_api_key': new_api_key,
        'modules_registry': modules_registry,
    })


@require_permission('system', 'edit')
@require_POST
def api_key_create(request):
    """Create a new API key — show plain key once via flash message."""

    name = request.POST.get('name', '').strip()

    if not name:
        messages.error(request, 'Key name is required.')
        return redirect('system:apis')

    inst, plain = ApiKey.generate(name=name, created_by=request.user.username)

    ## audit log
    try:
        from audit.models import AuditLog
        AuditLog.log(
            user=request.user,
            action='create',
            target_type='api_key',
            target_name=name,
            detail={
                'request': {
                    'method': 'POST',
                    'path': '/system/api-keys/create/',
                    'body': {'name': name}
                },
                'response': {'status_code': 302, 'key_prefix': inst.key_prefix}
            },
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    except Exception:
        pass

    ## store plain key in session — shown once on next page load
    request.session['new_api_key'] = plain
    return redirect('system:apis')


@require_permission('system', 'edit')
@require_POST
def api_key_toggle(request, key_id):
    """Enable or disable an API key."""

    key = get_object_or_404(ApiKey, pk=key_id)
    key.enabled = not key.enabled
    key.save(update_fields=['enabled'])
    messages.success(request, 'Key "%s" %s.' % (key.name, 'enabled' if key.enabled else 'disabled'))
    return redirect('system:apis')


@require_permission('system', 'edit')
@require_POST
def api_key_delete(request, key_id):
    """Delete an API key."""

    key = get_object_or_404(ApiKey, pk=key_id)
    name = key.name
    key.delete()
    messages.success(request, 'Key "%s" deleted.' % name)
    return redirect('system:apis')


## =============================================================
## Backup / Restore Views
## =============================================================

## module path constant — same pattern as modules/views.py
_MOD_PATH = str(settings.PROJ_PATH / 'mod')


@require_permission('system', 'edit')
def backup_view(request):
    """System backup/restore page."""

    return render(request, 'system/backup.html', {
        'nav_active': 'system',
    })


@require_permission('system', 'edit')
@require_POST
def backup_create(request):
    """
    Create and stream a ZIP backup of selected data types.

    Sections (selected via POST checkboxes):
      include_workflows  — each WfFlow as JSON
      include_modules    — .py files from mod/
      include_accounts   — users/groups/roles via Django serializer
      include_settings   — SystemSetting key-value store
    """

    include_workflows = request.POST.get('include_workflows') == 'on'
    include_modules   = request.POST.get('include_modules')   == 'on'
    include_accounts  = request.POST.get('include_accounts')  == 'on'
    include_settings  = request.POST.get('include_settings')  == 'on'

    if not any([include_workflows, include_modules, include_accounts, include_settings]):
        messages.error(request, 'Select at least one data type to back up.')
        return redirect('system:backup')

    buf = io.BytesIO()
    sections_included = []

    try:
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            ## metadata
            from django.utils import timezone as dj_tz
            meta = {
                'created_at': dj_tz.now().isoformat(),
                'created_by': request.user.username,
                'sections': [],
            }

            ## workflows
            if include_workflows:
                from workflows.models import WfFlow
                flows = WfFlow.objects.filter(deleted=False)
                for flow in flows:
                    data = {
                        'flow_name': flow.flow_name,
                        'enabled': flow.enabled,
                        'procedures': flow.get_procedures(),
                    }
                    zf.writestr('workflows/%s.json' % flow.flow_name, json.dumps(data, ensure_ascii=False, indent=2))
                meta['sections'].append('workflows')
                sections_included.append('workflows (%d)' % flows.count())

            ## modules
            if include_modules:
                mod_path = _MOD_PATH
                if os.path.isdir(mod_path):
                    for category in sorted(os.listdir(mod_path)):
                        cat_dir = os.path.join(mod_path, category)
                        if not os.path.isdir(cat_dir):
                            continue
                        for fname in sorted(os.listdir(cat_dir)):
                            if not fname.endswith('.py'):
                                continue
                            fpath = os.path.join(cat_dir, fname)
                            ## path safety — confirm within mod_path
                            if os.path.commonpath([os.path.realpath(fpath), os.path.realpath(mod_path)]) != os.path.realpath(mod_path):
                                continue
                            with open(fpath, 'r', encoding='utf-8') as mf:
                                zf.writestr('modules/%s/%s' % (category, fname), mf.read())
                meta['sections'].append('modules')
                sections_included.append('modules')

            ## accounts (users, groups, roles)
            if include_accounts:
                from django.core import serializers as dj_serializers
                from accounts.models import Role
                from django.contrib.auth.models import User, Group
                users_qs  = User.objects.filter(is_superuser=False)
                groups_qs = Group.objects.all()
                roles_qs  = Role.objects.all()
                accounts_data = {
                    'users':  json.loads(dj_serializers.serialize('json', users_qs)),
                    'groups': json.loads(dj_serializers.serialize('json', groups_qs)),
                    'roles':  json.loads(dj_serializers.serialize('json', roles_qs)),
                }
                zf.writestr('accounts.json', json.dumps(accounts_data, ensure_ascii=False, indent=2))
                meta['sections'].append('accounts')
                sections_included.append('accounts')

            ## settings
            if include_settings:
                settings_data = {s.key: s.value for s in SystemSetting.objects.all()}
                zf.writestr('settings.json', json.dumps(settings_data, ensure_ascii=False, indent=2))
                meta['sections'].append('settings')
                sections_included.append('settings')

            ## write metadata last
            zf.writestr('backup.json', json.dumps(meta, ensure_ascii=False, indent=2))

    except Exception as e:
        messages.error(request, 'Backup failed: %s' % str(e))
        return redirect('system:backup')

    buf.seek(0)
    from django.utils import timezone as dj_tz
    filename = 'workflow_backup_%s.zip' % dj_tz.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(buf.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


@require_permission('system', 'edit')
@require_POST
def backup_restore(request):
    """
    Restore data from an uploaded backup ZIP file.

    Each section is restored independently; errors in one section
    do not prevent others from being restored.
    """

    uploaded = request.FILES.get('backup_file')
    _restore_url = reverse('system:backup') + '?tab=restore'
    if not uploaded:
        messages.error(request, 'No file uploaded.')
        return redirect(_restore_url)

    restored = []
    errors   = []

    try:
        with zipfile.ZipFile(io.BytesIO(uploaded.read())) as zf:
            ## read metadata
            try:
                meta = json.loads(zf.read('backup.json'))
                sections = meta.get('sections', [])
            except Exception:
                messages.error(request, 'Invalid backup file: missing backup.json.')
                return redirect(_restore_url)

            ## restore workflows
            if 'workflows' in sections:
                try:
                    from workflows.models import WfFlow, WfVersion
                    from workflows.api_client import WorkflowAPIClient
                    client = WorkflowAPIClient()
                    count = 0
                    for name in zf.namelist():
                        if not name.startswith('workflows/') or not name.endswith('.json'):
                            continue
                        data = json.loads(zf.read(name))
                        flow_name = data.get('flow_name', '')
                        if not flow_name:
                            continue
                        procedures = data.get('procedures', {})

                        ## use API client so created_at/updated_at are set by DB
                        exists = WfFlow.objects.filter(flow_name=flow_name, deleted=False).exists()
                        if exists:
                            client.update_flow(flow_name, procedures)
                        else:
                            client.create_flow(flow_name, procedures)

                        ## create version snapshot
                        try:
                            WfVersion.create_version(
                                type=WfVersion.TYPE_FLOW,
                                target_name=flow_name,
                                content=json.dumps(procedures, ensure_ascii=False),
                                changed_by=request.user.username,
                            )
                        except Exception:
                            pass

                        count += 1
                    restored.append('workflows (%d)' % count)
                except Exception as e:
                    errors.append('workflows: %s' % str(e))

            ## restore modules
            if 'modules' in sections:
                try:
                    mod_path = _MOD_PATH
                    count = 0
                    for name in zf.namelist():
                        if not name.startswith('modules/') or not name.endswith('.py'):
                            continue
                        ## name is modules/<category>/<file>.py
                        parts = name.split('/', 2)
                        if len(parts) != 3:
                            continue
                        category, fname = parts[1], parts[2]

                        ## path safety
                        target = os.path.realpath(os.path.join(mod_path, category, fname))
                        if os.path.commonpath([target, os.path.realpath(mod_path)]) != os.path.realpath(mod_path):
                            continue

                        os.makedirs(os.path.join(mod_path, category), exist_ok=True)
                        with open(target, 'w', encoding='utf-8') as mf:
                            mf.write(zf.read(name).decode('utf-8'))
                        count += 1
                    restored.append('modules (%d files)' % count)
                except Exception as e:
                    errors.append('modules: %s' % str(e))

            ## restore accounts
            if 'accounts' in sections:
                try:
                    from django.core import serializers as dj_serializers
                    accounts_data = json.loads(zf.read('accounts.json'))
                    for model_key in ('groups', 'roles', 'users'):
                        if model_key not in accounts_data:
                            continue
                        obj_list = dj_serializers.deserialize('json', json.dumps(accounts_data[model_key]))
                        for obj in obj_list:
                            try:
                                obj.save()
                            except Exception:
                                pass
                    restored.append('accounts')
                except Exception as e:
                    errors.append('accounts: %s' % str(e))

            ## restore settings
            if 'settings' in sections:
                try:
                    settings_data = json.loads(zf.read('settings.json'))
                    for key, value in settings_data.items():
                        SystemSetting.set(key, value)
                    restored.append('settings')
                except Exception as e:
                    errors.append('settings: %s' % str(e))

    except zipfile.BadZipFile:
        messages.error(request, 'Uploaded file is not a valid ZIP archive.')
        return redirect(_restore_url)
    except Exception as e:
        messages.error(request, 'Restore failed: %s' % str(e))
        return redirect(_restore_url)

    if restored:
        messages.success(request, 'Restored: %s.' % ', '.join(restored))
    if errors:
        messages.warning(request, 'Errors during restore: %s.' % '; '.join(errors))

    return redirect(_restore_url)


## =============================================================
## SSL Certificates Views
## =============================================================

## base directory for cert storage — inside project, never public
_SSL_DIR = str(settings.PROJ_PATH / 'etc' / 'ssl')
_SSL_SERVER_CERT = str(settings.PROJ_PATH / 'etc' / 'ssl' / 'server.crt')
_SSL_SERVER_KEY  = str(settings.PROJ_PATH / 'etc' / 'ssl' / 'server.key')
## allowed certificate file extensions
_CERT_EXTENSIONS = {'.crt', '.pem', '.cer'}


def _parse_cert_info(cert_path: str) -> dict:
    """
    Parse basic certificate metadata: subject CN and expiry date.

    Args:
        cert_path (str): Path to a PEM certificate file

    Returns:
        dict: { 'cn': str, 'expiry': str, 'valid': bool }
    """

    info = {'cn': '', 'expiry': '', 'valid': False}
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        with open(cert_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        cn_attrs = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        info['cn'] = cn_attrs[0].value if cn_attrs else ''
        info['expiry'] = cert.not_valid_after_utc.strftime('%Y-%m-%d') if hasattr(cert, 'not_valid_after_utc') else str(cert.not_valid_after)
        info['valid'] = True
    except Exception:
        info['valid'] = False
    return info


## =============================================================
## SSH Key Management
## =============================================================

_SSH_DIR = str(settings.PROJ_PATH / 'etc' / 'ssh')
_SSH_DEFAULT_KEY = str(settings.PROJ_PATH / 'etc' / 'ssh' / 'default.key')


def _parse_ssh_key_info(path: str) -> dict:
    """
    Parse SSH private key metadata: type, bits, and fingerprint.

    Args:
        path (str): Path to a private key file

    Returns:
        dict: { 'type': str, 'bits': int, 'fingerprint': str }
              or None on failure
    """

    try:
        import paramiko
        import hashlib as _hl
        import base64

        ## try loading as different key types
        key = None
        key_type = 'Unknown'
        for cls, name in [
            (paramiko.RSAKey, 'RSA'),
            (paramiko.Ed25519Key, 'Ed25519'),
            (paramiko.ECDSAKey, 'ECDSA'),
            (paramiko.DSSKey, 'DSS'),
        ]:
            try:
                key = cls.from_private_key_file(path)
                key_type = name
                break
            except Exception:
                continue

        if key is None:
            return None

        ## compute fingerprint
        key_bytes = key.asbytes()
        digest = _hl.sha256(key_bytes).digest()
        fp = base64.b64encode(digest).decode('ascii').rstrip('=')

        return {
            'type': key_type,
            'bits': key.get_bits(),
            'fingerprint': 'SHA256:%s' % fp,
        }
    except Exception:
        return None


@require_permission('system', 'edit')
@require_POST
def ssh_key_upload(request):
    """
    Upload a default SSH private key.

    Validates the key using paramiko, stores to etc/ssh/default.key
    with mode 0o600, and saves the path in SystemSetting.
    """

    key_file = request.FILES.get('ssh_key_file')
    if not key_file:
        return JsonResponse({'status': False, 'error': 'No key file provided.'})

    try:
        import paramiko
        import tempfile

        ## write to temp file for validation
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.key')
        try:
            for chunk in key_file.chunks():
                tmp.write(chunk)
            tmp.close()

            ## validate by trying to load as SSH key
            key = None
            for cls in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]:
                try:
                    key = cls.from_private_key_file(tmp.name)
                    break
                except Exception:
                    continue

            if key is None:
                return JsonResponse({'status': False, 'error': 'Invalid SSH private key file.'})

            ## read validated key data
            with open(tmp.name, 'rb') as f:
                key_data = f.read()
        finally:
            os.unlink(tmp.name)

        ## ensure ssh dir exists
        os.makedirs(_SSH_DIR, exist_ok=True)

        ## write key with mode 0o600 (owner-only)
        fd = os.open(_SSH_DEFAULT_KEY, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(key_data)

        SystemSetting.set('ssh_default_key_path', _SSH_DEFAULT_KEY)

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='update',
                target_type='ssh_key',
                target_name='default',
                detail='Uploaded default SSH key: %s' % key_file.name,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        key_info = _parse_ssh_key_info(_SSH_DEFAULT_KEY)
        return JsonResponse({'status': True, 'key_info': key_info})

    ## error handling
    except Exception as e:
        return JsonResponse({'status': False, 'error': 'Failed to upload SSH key: %s' % str(e)})


@require_permission('system', 'edit')
@require_POST
def ssh_key_delete(request):
    """
    Delete the default SSH private key.

    Removes the key file from disk and clears the SystemSetting.
    """

    try:
        ## remove key file
        if os.path.isfile(_SSH_DEFAULT_KEY):
            os.remove(_SSH_DEFAULT_KEY)

        ## clear setting
        try:
            SystemSetting.objects.filter(key='ssh_default_key_path').delete()
        except Exception:
            pass

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='delete',
                target_type='ssh_key',
                target_name='default',
                detail='Deleted default SSH key',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return JsonResponse({'status': True})

    ## error handling
    except Exception as e:
        return JsonResponse({'status': False, 'error': 'Failed to delete SSH key: %s' % str(e)})


@require_permission('system', 'edit')
def ssl_view(request):
    """
    SSL Certificates management page — server certificate for HTTPS serving.
    """

    ## server cert info
    server_cert_info = None
    if os.path.isfile(_SSL_SERVER_CERT):
        server_cert_info = _parse_cert_info(_SSL_SERVER_CERT)

    ssl_server_enabled = SystemSetting.get('ssl_server_enabled', 'false') == 'true'

    return render(request, 'system/ssl.html', {
        'nav_active': 'system',
        'server_cert_info': server_cert_info,
        'ssl_server_enabled': ssl_server_enabled,
        'ssl_server_cert_path': _SSL_SERVER_CERT,
        'ssl_server_key_path': _SSL_SERVER_KEY,
    })


@require_permission('system', 'edit')
@require_POST
def ssl_server_upload(request):
    """
    Upload server certificate and private key files.

    Validates both files are valid PEM, stores to etc/ssl/.
    """

    cert_file = request.FILES.get('cert_file')
    key_file  = request.FILES.get('key_file')
    _ssl_url  = reverse('system:ssl') + '?tab=server'

    if not cert_file or not key_file:
        messages.error(request, 'Both certificate and key files are required.')
        return redirect(_ssl_url)

    ## validate extensions
    cert_ext = os.path.splitext(cert_file.name)[1].lower()
    key_ext  = os.path.splitext(key_file.name)[1].lower()
    if cert_ext not in _CERT_EXTENSIONS:
        messages.error(request, 'Certificate file must be .crt, .pem, or .cer')
        return redirect(_ssl_url)
    if key_ext not in {'.key', '.pem'}:
        messages.error(request, 'Key file must be .key or .pem')
        return redirect(_ssl_url)

    try:
        ## validate cert content
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        cert_data = cert_file.read()
        x509.load_pem_x509_certificate(cert_data, default_backend())

        ## ensure ssl dir exists
        os.makedirs(_SSL_DIR, exist_ok=True)

        ## write cert (mode 0o644)
        fd = os.open(_SSL_SERVER_CERT, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        with os.fdopen(fd, 'wb') as f:
            f.write(cert_data)

        ## write key (mode 0o600 — never publicly readable)
        key_data = key_file.read()
        fd = os.open(_SSL_SERVER_KEY, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(key_data)

        SystemSetting.set('ssl_server_cert_path', _SSL_SERVER_CERT)
        SystemSetting.set('ssl_server_key_path', _SSL_SERVER_KEY)

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='update',
                target_type='ssl_cert',
                target_name='server',
                detail='Uploaded server certificate: %s' % cert_file.name,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        messages.success(request, 'Server certificate and key uploaded successfully.')

    except Exception as e:
        messages.error(request, 'Invalid certificate file: %s' % str(e))

    return redirect(_ssl_url)


@require_permission('system', 'edit')
@require_POST
def ssl_server_toggle(request):
    """
    Enable or disable HTTPS for the gunicorn services.

    Updates etc/service.conf SSL_CERT_FILE / SSL_KEY_FILE variables,
    then restarts backend and frontend services.
    """

    _ssl_url = reverse('system:ssl') + '?tab=server'
    action   = request.POST.get('action', 'enable')

    try:
        conf_path = str(settings.PROJ_PATH / 'etc' / 'service.conf')
        with open(conf_path, 'r', encoding='utf-8') as f:
            conf_content = f.read()

        if action == 'enable':
            ## validate cert and key exist
            if not os.path.isfile(_SSL_SERVER_CERT) or not os.path.isfile(_SSL_SERVER_KEY):
                messages.error(request, 'Certificate and key must be uploaded before enabling HTTPS.')
                return redirect(_ssl_url)

            ## add or update SSL vars in service.conf
            ssl_block = (
                '\n## SSL certificate settings\n'
                'SSL_CERT_FILE=%s\n'
                'SSL_KEY_FILE=%s\n'
            ) % (_SSL_SERVER_CERT, _SSL_SERVER_KEY)

            ## remove existing ssl block if present
            conf_content = re.sub(r'\n## SSL certificate settings\nSSL_CERT_FILE=.*\nSSL_KEY_FILE=.*\n', '', conf_content)
            conf_content = conf_content.rstrip('\n') + ssl_block

            SystemSetting.set('ssl_server_enabled', 'true')
            msg = 'HTTPS enabled. Services are restarting. Please access the UI via https:// after restart.'
            audit_detail = 'Enabled HTTPS with cert: %s' % _SSL_SERVER_CERT

        else:
            ## remove ssl block
            conf_content = re.sub(r'\n## SSL certificate settings\nSSL_CERT_FILE=.*\nSSL_KEY_FILE=.*\n', '', conf_content)
            if not conf_content.endswith('\n'):
                conf_content += '\n'

            SystemSetting.set('ssl_server_enabled', 'false')
            msg = 'HTTPS disabled. Services are restarting...'
            audit_detail = 'Disabled HTTPS'

        ## write updated conf
        with open(conf_path, 'w', encoding='utf-8') as f:
            f.write(conf_content)

        ## restart services
        ## backend can be restarted inline (separate process)
        ## frontend must be deferred — killing it inline kills THIS request
        proj_path = str(settings.PROJ_PATH)
        script_path = os.path.join(proj_path, 'bin/service.sh')
        if os.path.isfile(script_path):
            ## restart backend immediately
            _stop_service('5001')
            subprocess.Popen(
                ['bash', script_path, 'start', 'backend'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            ## defer frontend restart so the HTTP response can be sent first
            subprocess.Popen(
                ['bash', '-c', 'sleep 2 && bash %s restart frontend' % script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='update',
                target_type='ssl_cert',
                target_name='server',
                detail=audit_detail,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        messages.success(request, msg)

    except Exception as e:
        messages.error(request, 'Failed to toggle HTTPS: %s' % str(e))

    return redirect(_ssl_url)


@require_permission('system', 'edit')
@require_POST
def ssl_server_delete(request):
    """
    Delete the server certificate and key files, and disable HTTPS.
    """

    _ssl_url = reverse('system:ssl') + '?tab=server'

    try:
        for fpath in (_SSL_SERVER_CERT, _SSL_SERVER_KEY):
            if os.path.isfile(fpath):
                os.remove(fpath)

        SystemSetting.set('ssl_server_enabled', 'false')

        ## remove ssl block from service.conf
        conf_path = str(settings.PROJ_PATH / 'etc' / 'service.conf')
        with open(conf_path, 'r', encoding='utf-8') as f:
            conf_content = f.read()
        conf_content = re.sub(r'\n## SSL certificate settings\nSSL_CERT_FILE=.*\nSSL_KEY_FILE=.*\n', '', conf_content)
        with open(conf_path, 'w', encoding='utf-8') as f:
            f.write(conf_content)

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='delete',
                target_type='ssl_cert',
                target_name='server',
                detail='Deleted server certificate and key',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        messages.success(request, 'Server certificate deleted.')

    except Exception as e:
        messages.error(request, 'Failed to delete certificate: %s' % str(e))

    return redirect(_ssl_url)


## =============================================================
## Services Views
## =============================================================

## service definitions: name → port + service script
_SERVICES = {
    'backend':  {'port': 5001, 'script': 'bin/service.sh',  'label': 'Flask API (Backend)'},
    'frontend': {'port': 5002, 'script': 'bin/service.sh', 'label': 'Django UI (Frontend)'},
}


def _get_service_pid(port: int):
    """
    Return the PID of the process listening on the given port, or None.

    Args:
        port (int): TCP port to check

    Returns:
        int or None: PID if running, None if not
    """

    try:
        result = subprocess.run(
            ['lsof', '-ti', 'tcp:%d' % port],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split('\n')
        pids = [p for p in pids if p.strip().isdigit()]
        return int(pids[0]) if pids else None
    except Exception:
        return None


def _stop_service(port: int) -> bool:
    """
    Stop all processes listening on the given port via SIGTERM,
    falling back to SIGKILL for any that refuse to stop.

    Args:
        port (int): TCP port

    Returns:
        bool: True if process(es) were found and signalled
    """

    try:
        result = subprocess.run(
            ['lsof', '-ti', 'tcp:%d' % port],
            capture_output=True, text=True, timeout=5
        )
        pids = [int(p) for p in result.stdout.strip().split('\n') if p.strip().isdigit()]
    except Exception:
        pids = []

    if not pids:
        return False

    ## send SIGTERM to all
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    ## wait for port to clear
    for _ in range(40):
        time.sleep(0.1)
        if _get_service_pid(port) is None:
            return True

    ## force kill remaining
    try:
        result = subprocess.run(
            ['lsof', '-ti', 'tcp:%d' % port],
            capture_output=True, text=True, timeout=5
        )
        remaining = [int(p) for p in result.stdout.strip().split('\n') if p.strip().isdigit()]
        for pid in remaining:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except Exception:
        pass

    return True


def _read_service_conf() -> dict:
    """
    Parse etc/service.conf into a dict of key-value pairs.

    Returns:
        dict: Configuration variables
    """

    conf = {}
    try:
        conf_path = str(settings.PROJ_PATH / 'etc' / 'service.conf')
        with open(conf_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    conf[key.strip()] = val.strip()
    except Exception:
        pass
    return conf


def _write_service_conf(updates: dict):
    """
    Update specific keys in etc/service.conf while preserving comments and structure.

    Args:
        updates (dict): { 'KEY': 'new_value', ... } to update

    Raises:
        Exception: on file read/write failure
    """

    conf_path = str(settings.PROJ_PATH / 'etc' / 'service.conf')
    with open(conf_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key, _, _ = stripped.partition('=')
            key = key.strip()
            if key in updates:
                new_lines.append('%s=%s\n' % (key, updates[key]))
                continue
        new_lines.append(line)

    with open(conf_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def _sync_global_json_ports(updates: dict):
    """
    Sync port changes from service.conf keys to etc/global.json.

    Maps: BACKEND_PORT → api.port, FRONTEND_PORT → web.port
    """

    port_map = {
        'BACKEND_PORT':  'api',
        'FRONTEND_PORT': 'web',
    }

    ## check if any port keys changed
    changed = {port_map[k]: int(v) for k, v in updates.items() if k in port_map}
    if not changed:
        return

    ## read global.json
    gj_path = str(settings.PROJ_PATH / 'etc' / 'global.json')
    with open(gj_path, 'r', encoding='utf-8') as f:
        cfg = json5.load(f)

    ## update port values
    for section, port in changed.items():
        if section in cfg:
            cfg[section]['port'] = port

    ## write back
    with open(gj_path, 'w', encoding='utf-8') as f:
        json5.dump(cfg, f, indent=2, trailing_commas=True)
        f.write('\n')


def _read_global_json_flat():
    """
    Read etc/global.json and return a flattened dict with dot-notation keys.

    Masks db.password and web.secret_key with '****'.
    """

    gj_path = str(settings.PROJ_PATH / 'etc' / 'global.json')
    try:
        with open(gj_path, 'r', encoding='utf-8') as f:
            gj_raw = json5.load(f)

        flat = {}
        for section, vals in gj_raw.items():
            if isinstance(vals, dict):
                for k, v in vals.items():
                    if isinstance(v, dict):
                        for k2, v2 in v.items():
                            flat['%s.%s.%s' % (section, k, k2)] = v2
                    else:
                        display_key = '%s.%s' % (section, k)
                        ## mask sensitive fields
                        if k in ('password', 'secret_key'):
                            flat[display_key] = '****'
                        else:
                            flat[display_key] = v
            else:
                flat[section] = vals
        return flat
    except Exception:
        return {}


@require_permission('system', 'edit')
def services_view(request):
    """
    Services management page.

    Shows status, config, and recent log entries for backend and frontend services.
    """

    conf = _read_service_conf()
    services = {}

    ## per-service log queries
    _LOG_QUERIES = {
        'backend': (
            "SELECT created_at, level, message FROM"
            " (SELECT created_at, level, message FROM wf_syslog ORDER BY id DESC LIMIT 50) t"
            " ORDER BY created_at ASC"
        ),
        'frontend': (
            "SELECT created_at, level, message FROM"
            " (SELECT created_at, level, message FROM wf_reqlog ORDER BY id DESC LIMIT 50) t"
            " ORDER BY created_at ASC"
        ),
    }

    for svc_name, svc_info in _SERVICES.items():
        pid = _get_service_pid(svc_info['port'])

        ## build per-service config subset from service.conf
        svc_conf_keys = {
            'backend':  ['BACKEND_HOST', 'BACKEND_PORT', 'BACKEND_WORKERS', 'BACKEND_THREADS', 'BACKEND_TIMEOUT'],
            'frontend': ['FRONTEND_HOST', 'FRONTEND_PORT', 'FRONTEND_WORKERS', 'FRONTEND_THREADS', 'FRONTEND_TIMEOUT'],
        }
        svc_config = {k: conf[k] for k in svc_conf_keys.get(svc_name, []) if k in conf}

        ## fetch last 50 log entries for this service
        svc_logs = []
        try:
            sql = _LOG_QUERIES.get(svc_name)
            if sql:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                svc_logs = [
                    {'created_at': str(row[0]), 'level': row[1], 'message': str(row[2])[:500]}
                    for row in rows
                ]
        except Exception:
            pass

        services[svc_name] = {
            'label': svc_info['label'],
            'port': svc_info['port'],
            'running': pid is not None,
            'pid': pid,
            'config': svc_config,
            'logs': svc_logs,
        }

    ## read global.json for display
    global_json = _read_global_json_flat()

    ## SSH key info
    ssh_key_exists = os.path.isfile(_SSH_DEFAULT_KEY)
    ssh_key_info = _parse_ssh_key_info(_SSH_DEFAULT_KEY) if ssh_key_exists else None

    return render(request, 'system/services.html', {
        'nav_active': 'system',
        'services': services,
        'global_json': global_json,
        'ssh_key_exists': ssh_key_exists,
        'ssh_key_info': ssh_key_info,
        'ssh_key_path': _SSH_DEFAULT_KEY,
    })


@require_permission('system', 'edit')
@require_POST
def service_start(request, svc):
    """
    Start a service by name (backend or frontend).
    """

    ## validate service name against allowlist
    if svc not in _SERVICES:
        return JsonResponse({'status': False, 'error': 'Unknown service: %s' % svc})

    svc_info = _SERVICES[svc]
    port = svc_info['port']
    script_path = str(settings.PROJ_PATH / svc_info['script'])

    ## check if already running
    if _get_service_pid(port):
        return JsonResponse({'status': False, 'error': 'Service is already running on port %d' % port})

    try:
        subprocess.Popen(
            ['bash', script_path, 'start', svc],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='enable',
                target_type='service',
                target_name=svc,
                detail={
                    'request': {'action': 'start', 'service': svc, 'port': port},
                    'response': {'status': True, 'message': 'Started %s service' % svc_info['label']},
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return JsonResponse({'status': True, 'running': True, 'message': '%s started' % svc_info['label']})

    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)})


@require_permission('system', 'edit')
@require_POST
def service_stop(request, svc):
    """
    Stop a service by name (backend or frontend).
    """

    ## validate service name against allowlist
    if svc not in _SERVICES:
        return JsonResponse({'status': False, 'error': 'Unknown service: %s' % svc})

    svc_info = _SERVICES[svc]
    port = svc_info['port']

    pid = _get_service_pid(port)
    if not pid:
        return JsonResponse({'status': False, 'error': 'Service is not running'})

    try:
        _stop_service(port)

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='disable',
                target_type='service',
                target_name=svc,
                detail={
                    'request': {'action': 'stop', 'service': svc, 'port': port, 'pid': pid},
                    'response': {'status': True, 'message': 'Stopped %s service' % svc_info['label']},
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return JsonResponse({'status': True, 'running': False, 'message': '%s stopped' % svc_info['label']})

    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)})


@require_permission('system', 'edit')
@require_POST
def service_restart(request, svc):
    """
    Restart a service by name (backend or frontend).
    """

    ## validate service name against allowlist
    if svc not in _SERVICES:
        return JsonResponse({'status': False, 'error': 'Unknown service: %s' % svc})

    svc_info = _SERVICES[svc]
    port = svc_info['port']
    script_path = str(settings.PROJ_PATH / svc_info['script'])

    try:
        ## stop existing process
        _stop_service(port)

        ## start fresh
        subprocess.Popen(
            ['bash', script_path, 'start', svc],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        ## audit log
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='update',
                target_type='service',
                target_name=svc,
                detail={
                    'request': {'action': 'restart', 'service': svc, 'port': port},
                    'response': {'status': True, 'message': 'Restarted %s service' % svc_info['label']},
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return JsonResponse({'status': True, 'running': True, 'message': '%s restarted' % svc_info['label']})

    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)})


@require_permission('system', 'edit')
def service_status(request, svc):
    """
    Return current running status of a service as JSON (GET).
    """

    ## validate service name against allowlist
    if svc not in _SERVICES:
        return JsonResponse({'status': False, 'error': 'Unknown service: %s' % svc})

    svc_info = _SERVICES[svc]
    pid = _get_service_pid(svc_info['port'])
    return JsonResponse({
        'status': True,
        'running': pid is not None,
        'pid': pid,
    })


@require_permission('system', 'edit')
def service_logs(request, svc):
    """
    Return the last 50 log entries as JSON (GET).

    Backend reads from wf_syslog (WorkFlow engine logs).
    Frontend reads from wf_reqlog (Django HTTP request logs).
    """

    ## validate service name against allowlist
    if svc not in _SERVICES:
        return JsonResponse({'status': False, 'error': 'Unknown service: %s' % svc})

    ## per-service log table
    log_table = 'wf_syslog' if svc == 'backend' else 'wf_reqlog'

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT created_at, level, message FROM"
                " (SELECT created_at, level, message FROM %s ORDER BY id DESC LIMIT 50) t"
                " ORDER BY created_at ASC" % log_table
            )
            rows = cursor.fetchall()

        logs = [
            {'created_at': str(row[0]), 'level': row[1], 'message': str(row[2])[:500]}
            for row in rows
        ]
        return JsonResponse({'status': True, 'logs': logs})

    ## error handling
    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)})


## =============================================================
## Service Config Update
## =============================================================

## editable config keys per service with validation rules (min, max)
_SVC_CONFIG_EDITABLE = {
    'backend': {
        'BACKEND_HOST':    {'type': 'str'},
        'BACKEND_PORT':    {'type': 'int', 'min': 1024, 'max': 65535},
        'BACKEND_WORKERS': {'type': 'int', 'min': 1, 'max': 32},
        'BACKEND_THREADS': {'type': 'int', 'min': 1, 'max': 64},
        'BACKEND_TIMEOUT': {'type': 'int', 'min': 10, 'max': 600},
    },
    'frontend': {
        'FRONTEND_HOST':    {'type': 'str'},
        'FRONTEND_PORT':    {'type': 'int', 'min': 1024, 'max': 65535},
        'FRONTEND_WORKERS': {'type': 'int', 'min': 1, 'max': 32},
        'FRONTEND_THREADS': {'type': 'int', 'min': 1, 'max': 64},
        'FRONTEND_TIMEOUT': {'type': 'int', 'min': 10, 'max': 600},
    },
}


@require_permission('system', 'edit')
@require_POST
def service_config_update(request, svc):
    """
    AJAX endpoint — update service configuration in etc/service.conf.

    Accepts JSON body with config key-value pairs.
    Returns JSON: { status, message }
    """

    ## validate service name against allowlist
    if svc not in _SVC_CONFIG_EDITABLE:
        return JsonResponse({'status': False, 'error': 'Unknown service: %s' % svc})

    ## load args
    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': False, 'error': 'Invalid JSON body'}, status=400)

    if not isinstance(payload, dict) or not payload:
        return JsonResponse({'status': False, 'error': 'No config values provided'}, status=400)

    allowed_keys = _SVC_CONFIG_EDITABLE[svc]
    old_conf = _read_service_conf()
    updates = {}
    errors = []

    for key, value in payload.items():
        ## validate key is allowed
        if key not in allowed_keys:
            errors.append('%s: not an editable setting' % key)
            continue

        rule = allowed_keys[key]
        value = str(value).strip()

        ## validate value
        if rule['type'] == 'str':
            if not value:
                errors.append('%s: cannot be empty' % key)
                continue
        elif rule['type'] == 'int':
            try:
                int_val = int(value)
            except (ValueError, TypeError):
                errors.append('%s: must be an integer' % key)
                continue
            if int_val < rule['min'] or int_val > rule['max']:
                errors.append('%s: must be between %d and %d' % (key, rule['min'], rule['max']))
                continue
            value = str(int_val)

        updates[key] = value

    if errors:
        return JsonResponse({'status': False, 'error': '; '.join(errors)})

    if not updates:
        return JsonResponse({'status': False, 'error': 'No valid changes to save'})

    ## try:
    try:
        _write_service_conf(updates)
        _sync_global_json_ports(updates)

        ## audit log
        try:
            from audit.models import AuditLog
            changes = {}
            for k, v in updates.items():
                old_val = old_conf.get(k, '')
                if old_val != v:
                    changes[k] = {'old': old_val, 'new': v}
            if changes:
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='service_config',
                    target_name=svc,
                    detail={
                        'request': {'action': 'config_update', 'service': svc, 'changes': changes},
                        'response': {'status': True, 'message': 'Configuration saved'},
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
        except Exception:
            pass

        return JsonResponse({
            'status': True,
            'message': 'Configuration saved. Restart service to apply changes.',
        })

    ## error handling
    except Exception as e:
        return JsonResponse({'status': False, 'error': 'Failed to save: %s' % str(e)})


@require_permission('system', 'edit')
@require_POST
def verify_password(request):
    """
    AJAX endpoint — verify current user's password to reveal sensitive config.

    Accepts JSON body with 'password' field.
    Returns JSON: { status, value } on success, { status, error } on failure.
    """

    ## load args
    try:
        payload = json.loads(request.body)
        password = payload.get('password', '')
    except Exception:
        return JsonResponse({'status': False, 'error': 'Invalid request'}, status=400)

    if not password:
        return JsonResponse({'status': False, 'error': 'Password is required'})

    ## verify password
    if request.user.check_password(password):
        ## read actual password from global.json
        try:
            gj_path = str(settings.PROJ_PATH / 'etc' / 'global.json')
            with open(gj_path, 'r', encoding='utf-8') as f:
                cfg = json5.load(f)
            return JsonResponse({'status': True, 'value': cfg.get('db', {}).get('password', '')})
        ## error handling
        except Exception as e:
            return JsonResponse({'status': False, 'error': 'Failed to read config: %s' % str(e)})

    return JsonResponse({'status': False, 'error': 'Incorrect password'})
