"""
Workflows Views

Handles workflow listing, editing (dual-mode editor),
and actions (create, delete, enable, disable, rename, run).
"""

## import buildin pkgs
import json
from datetime import datetime
from urllib.parse import urlencode

## import django pkgs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator

from .models import WfFlow, WfRunHistory, WfRunStep, WfVersion
from .api_client import WorkflowAPIClient
from accounts.decorators import require_permission


## safe request headers to capture — never include Cookie/Authorization
_HEADER_MAP = {
    'HTTP_USER_AGENT': 'User-Agent',
    'HTTP_REFERER': 'Referer',
    'HTTP_HOST': 'Host',
    'HTTP_ACCEPT': 'Accept',
    'HTTP_ACCEPT_LANGUAGE': 'Accept-Language',
    'HTTP_ACCEPT_ENCODING': 'Accept-Encoding',
    'HTTP_CONNECTION': 'Connection',
    'CONTENT_TYPE': 'Content-Type',
    'CONTENT_LENGTH': 'Content-Length',
}


def _get_flow_or_not_found(request, flow_name):
    """Return (flow, None) or (None, error_response) for missing/deleted workflows."""

    try:
        flow = WfFlow.objects.get(flow_name=flow_name, deleted=False)
        return flow, None
    except WfFlow.DoesNotExist:
        return None, render(request, 'workflows/flow_not_found.html', {
            'nav_active': 'workflows',
            'flow_name': flow_name,
        })


def _get_request_headers(request):
    """Extract safe HTTP request headers from request.META."""

    headers = {}
    for meta_key, header_name in _HEADER_MAP.items():
        val = request.META.get(meta_key)
        if val:
            headers[header_name] = val
    return headers


def _parse_datetime(value):
    """
    Parse datetime string from flatpickr input.

    Supports formats: YYYY-MM-DDTHH:MM, YYYY-MM-DD HH:MM, YYYY-MM-DD
    Returns datetime object or None.
    """

    if not value:
        return None

    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def get_api_client():
    """Get a WorkflowAPIClient instance."""
    return WorkflowAPIClient()


@require_permission('workflows', 'view')
def flow_list(request):
    """List all non-deleted workflows with pagination."""

    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    flows_qs = WfFlow.objects.filter(deleted=False).order_by('flow_name')

    paginator = Paginator(flows_qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    ## annotate each flow with its latest run
    for flow in page_obj:
        flow.last_run = WfRunHistory.objects.filter(
            flow_name=flow.flow_name
        ).first()  ## ordered by -start_time from Meta

    ## auto-create v1 version snapshot for any workflow with no version history yet
    ## (e.g. workflows that existed before versioning was introduced)
    for flow in page_obj:
        try:
            if not WfVersion.objects.filter(type=WfVersion.TYPE_FLOW, target_name=flow.flow_name).exists():
                content = json.dumps(
                    flow.flow_procedures if isinstance(flow.flow_procedures, dict) else json.loads(flow.flow_procedures),
                    ensure_ascii=False,
                )
                WfVersion.create_version(
                    type=WfVersion.TYPE_FLOW,
                    target_name=flow.flow_name,
                    content=content,
                    changed_by='system',
                )
        except Exception:
            pass

    return render(request, 'workflows/flow_list.html', {
        'nav_active': 'workflows',
        'flows': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
    })


@require_permission('workflows', 'create')
def flow_create(request):
    """Create a new workflow via the dual-mode editor."""

    if request.method == 'POST':
        flow_name = request.POST.get('flow_name', '').strip()
        procedures_json = request.POST.get('procedures_json', '{}')

        if not flow_name:
            messages.error(request, 'Flow name is required.')
            return render(request, 'workflows/flow_edit.html', {
                'nav_active': 'workflows',
                'is_create': True,
                'flow_name': flow_name,
                'procedures_json': procedures_json,
            })

        ## parse procedures
        try:
            data = json.loads(procedures_json)
            procedures = data.get('procedures', [])
            variables = data.get('variables', {})
            connections = data.get('_connections', None)
            positions = data.get('_positions', None)
        except json.JSONDecodeError as e:
            messages.error(request, 'Invalid JSON: %s' % e)
            return render(request, 'workflows/flow_edit.html', {
                'nav_active': 'workflows',
                'is_create': True,
                'flow_name': flow_name,
                'procedures_json': procedures_json,
            })

        ## call API
        client = get_api_client()
        result = client.create_flow(flow_name, procedures, variables=variables, connections=connections, positions=positions)

        if result.get('status'):
            ## save initial version
            try:
                WfVersion.create_version(
                    type=WfVersion.TYPE_FLOW,
                    target_name=flow_name,
                    content=procedures_json,
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
                    target_type='flow',
                    target_name=flow_name,
                    detail={
                        'request': {
                            'method': request.method,
                            'path': request.path,
                            'headers': _get_request_headers(request),
                            'body': {
                                'step_count': len(procedures),
                                'steps': [p.get('name', '') for p in procedures],
                                'procedures': procedures,
                            },
                        },
                        'response': {
                            'status_code': 200,
                            'location': '/workflows/',
                        },
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" created successfully.' % flow_name)
            return redirect('workflows:flow_list')
        else:
            messages.error(request, 'Failed to create workflow: %s' % result.get('error', 'Unknown error'))

    return render(request, 'workflows/flow_edit.html', {
        'nav_active': 'workflows',
        'is_create': True,
        'flow_name': '',
        'procedures_json': '{"procedures": []}',
    })


@require_permission('workflows', 'edit')
def flow_edit(request, flow_name):
    """Edit an existing workflow via the dual-mode editor."""

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp
    procedures_data = flow.get_procedures()

    if request.method == 'POST':
        procedures_json = request.POST.get('procedures_json', '{}')
        new_flow_name = request.POST.get('flow_name', '').strip()
        original_flow_name = request.POST.get('original_flow_name', flow_name)

        ## parse procedures
        try:
            data = json.loads(procedures_json)
            procedures = data.get('procedures', [])
            variables = data.get('variables', {})
            connections = data.get('_connections', None)
            positions = data.get('_positions', None)
        except json.JSONDecodeError as e:
            messages.error(request, 'Invalid JSON: %s' % e)
            return render(request, 'workflows/flow_edit.html', {
                'nav_active': 'workflows',
                'is_create': False,
                'flow_name': flow_name,
                'procedures_json': procedures_json,
            })

        ## check if rename requested
        needs_rename = new_flow_name and new_flow_name != flow_name

        ## skip save if nothing changed and no rename
        current_content = json.dumps(procedures_data, indent=4, ensure_ascii=False)
        new_content = json.dumps(data, indent=4, ensure_ascii=False)
        if current_content == new_content and not needs_rename:
            messages.info(request, 'No changes detected.')
            return redirect('workflows:flow_edit', flow_name=flow_name)

        ## save current version BEFORE the update
        try:
            WfVersion.create_version(
                type=WfVersion.TYPE_FLOW,
                target_name=flow_name,
                content=current_content,
                changed_by=request.user.username,
            )
        except Exception:
            pass

        ## call API to update procedures
        client = get_api_client()
        result = client.update_flow(flow_name, procedures, variables=variables, connections=connections, positions=positions)

        if result.get('status'):
            ## handle rename if name changed
            if needs_rename:
                try:
                    rename_result = client.rename_flow(flow_name, new_flow_name)
                    if rename_result.get('status'):
                        ## update Django model flow_name
                        flow.flow_name = new_flow_name
                        flow.save()
                        flow_name = new_flow_name
                    else:
                        messages.warning(request, 'Procedures saved but rename failed: %s' % rename_result.get('error', 'Unknown'))
                except Exception as e:
                    messages.warning(request, 'Procedures saved but rename failed: %s' % e)

            ## save new version AFTER the update so runlog can find it
            try:
                WfVersion.create_version(
                    type=WfVersion.TYPE_FLOW,
                    target_name=flow_name,
                    content=new_content,
                    changed_by=request.user.username,
                )
            except Exception:
                pass

            ## log audit
            try:
                from audit.models import AuditLog
                ## compute added/removed/changed steps
                old_steps = {p.get('name'): p for p in (procedures_data.get('procedures', []) if isinstance(procedures_data, dict) else [])}
                new_steps = {p.get('name'): p for p in procedures}
                added = [n for n in new_steps if n not in old_steps]
                removed = [n for n in old_steps if n not in new_steps]
                modified = [n for n in new_steps if n in old_steps and new_steps[n] != old_steps[n]]
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='flow',
                    target_name=flow_name,
                    detail={
                        'request': {
                            'method': request.method,
                            'path': request.path,
                            'headers': _get_request_headers(request),
                            'body': {
                                'step_count': len(procedures),
                                'steps_added': added,
                                'steps_removed': removed,
                                'steps_modified': modified,
                                'procedures': procedures,
                            },
                        },
                        'response': {
                            'status_code': 200,
                            'location': '/workflows/',
                        },
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" updated successfully.' % flow_name)
            return redirect('workflows:flow_list')
        else:
            messages.error(request, 'Failed to update workflow: %s' % result.get('error', 'Unknown error'))

    procedures_json = json.dumps(procedures_data, indent=4, ensure_ascii=False)

    return render(request, 'workflows/flow_edit.html', {
        'nav_active': 'workflows',
        'is_create': False,
        'flow_name': flow_name,
        'procedures_json': procedures_json,
    })


@require_permission('workflows', 'delete')
def flow_delete(request, flow_name):
    """Delete a workflow (soft delete via API)."""

    if request.method == 'POST':
        client = get_api_client()
        result = client.delete_flow(flow_name)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='delete',
                    target_type='flow',
                    target_name=flow_name,
                    detail={
                        'request': {
                            'method': request.method,
                            'path': request.path,
                            'headers': _get_request_headers(request),
                            'body': {'flow_name': flow_name},
                        },
                        'response': {
                            'status_code': 200,
                            'location': '/workflows/',
                        },
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" deleted.' % flow_name)
        else:
            messages.error(request, 'Failed to delete workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@require_permission('workflows', 'enable')
def flow_enable(request, flow_name):
    """Enable a workflow via API."""

    if request.method == 'POST':
        client = get_api_client()
        result = client.enable_flow(flow_name)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='enable',
                    target_type='flow',
                    target_name=flow_name,
                    detail={
                        'request': {
                            'method': request.method,
                            'path': request.path,
                            'headers': _get_request_headers(request),
                            'body': {'enabled': True},
                        },
                        'response': {
                            'status_code': 200,
                            'location': '/workflows/',
                        },
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" enabled.' % flow_name)
        else:
            messages.error(request, 'Failed to enable workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@require_permission('workflows', 'enable')
def flow_disable(request, flow_name):
    """Disable a workflow via API."""

    if request.method == 'POST':
        client = get_api_client()
        result = client.disable_flow(flow_name)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='disable',
                    target_type='flow',
                    target_name=flow_name,
                    detail={
                        'request': {
                            'method': request.method,
                            'path': request.path,
                            'headers': _get_request_headers(request),
                            'body': {'enabled': False},
                        },
                        'response': {
                            'status_code': 200,
                            'location': '/workflows/',
                        },
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" disabled.' % flow_name)
        else:
            messages.error(request, 'Failed to disable workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@require_permission('workflows', 'run')
def flow_run(request, flow_name):
    """Execute a workflow via API and redirect to run detail page."""

    if request.method == 'POST':
        client = get_api_client()
        result = client.run_flow(flow_name, trigger_by=request.user.username)

        ## log audit
        try:
            from audit.models import AuditLog
            AuditLog.log(
                user=request.user,
                action='run',
                target_type='flow',
                target_name=flow_name,
                detail={
                    'request': {
                        'method': request.method,
                        'path': request.path,
                        'headers': _get_request_headers(request),
                    },
                    'response': {
                        'status_code': 200,
                        'run_id': result.get('run_id'),
                        'status': result.get('status'),
                        'trigger_by': request.user.username,
                    },
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        run_id = result.get('run_id')
        if run_id:
            ## redirect to run detail page
            return redirect('workflows:flow_run_detail', flow_name=flow_name, run_id=run_id)
        elif result.get('status'):
            messages.success(request, 'Workflow "%s" executed successfully.' % flow_name)
        else:
            messages.error(request, 'Failed to run workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@require_permission('workflows', 'edit')
def flow_rename(request, flow_name):
    """Rename a workflow via API."""

    if request.method == 'POST':
        new_name = request.POST.get('new_name', '').strip()

        if not new_name:
            messages.error(request, 'New name is required.')
            return redirect('workflows:flow_list')

        client = get_api_client()
        result = client.rename_flow(flow_name, new_name)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='rename',
                    target_type='flow',
                    target_name='%s -> %s' % (flow_name, new_name),
                    detail={
                        'request': {
                            'method': request.method,
                            'path': request.path,
                            'headers': _get_request_headers(request),
                            'body': {'from': flow_name, 'to': new_name},
                        },
                        'response': {
                            'status_code': 200,
                            'location': '/workflows/',
                        },
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow renamed from "%s" to "%s".' % (flow_name, new_name))
        else:
            messages.error(request, 'Failed to rename workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@require_permission('workflows', 'run')
def flow_run_detail(request, flow_name, run_id):
    """Show run detail with visual step-by-step status."""

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp
    run = get_object_or_404(WfRunHistory, pk=run_id, flow_name=flow_name)
    steps = list(WfRunStep.objects.filter(run=run).order_by('step_order'))

    ## recent runs — paginated
    runs_qs = WfRunHistory.objects.filter(flow_name=flow_name)
    runs_paginator = Paginator(runs_qs, 10)
    runs_page_obj = runs_paginator.get_page(request.GET.get('runs_page', 1))

    ## format result_data for template display
    for s in steps:
        if s.result_data:
            s.result_data_display = json.dumps(s.result_data, indent=2, ensure_ascii=False)
        else:
            s.result_data_display = None

    ## build step results for JS
    step_results = []
    for s in steps:
        step_results.append({
            'name': s.step_name,
            'order': s.step_order,
            'status': s.status,
            'start_time': str(s.start_time) if s.start_time else None,
            'end_time': str(s.end_time) if s.end_time else None,
            'duration_ms': s.duration_ms,
            'result_data': s.result_data,
            'error_msg': s.error_msg,
        })

    ## flowchart snapshot — use flow version active at run time
    using_snapshot = False
    snap = WfVersion.objects.filter(
        type=WfVersion.TYPE_FLOW,
        target_name=flow_name,
        created_at__lte=run.start_time,
    ).order_by('-created_at').first()

    if snap:
        try:
            content = json.loads(snap.content)
            if isinstance(content, dict) and 'procedures' in content:
                procedures_data = content
                using_snapshot = True
            else:
                procedures_data = flow.get_procedures()
        except Exception:
            procedures_data = flow.get_procedures()
    else:
        procedures_data = flow.get_procedures()

    procedures_json = json.dumps(procedures_data, ensure_ascii=False)

    return render(request, 'workflows/flow_run_detail.html', {
        'nav_active': 'workflows',
        'flow': flow,
        'run': run,
        'steps': steps,
        'runs_page_obj': runs_page_obj,
        'procedures_json': procedures_json,
        'step_results_json': json.dumps(step_results, ensure_ascii=False),
        'using_snapshot': using_snapshot,
    })


@require_permission('workflows', 'run')
def flow_run_history(request, flow_name):
    """Show all run history for a workflow."""

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp

    ## base queryset
    qs = WfRunHistory.objects.filter(flow_name=flow_name).order_by('-start_time')

    ## apply filters
    filter_status = request.GET.get('status', '')
    filter_trigger = request.GET.get('trigger', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')
    filter_search = request.GET.get('search', '')

    if filter_status:
        qs = qs.filter(status=filter_status)

    if filter_trigger == 'job':
        qs = qs.filter(trigger_by__startswith='job:')
    elif filter_trigger == 'manual':
        qs = qs.exclude(trigger_by__startswith='job:')

    dt_from = _parse_datetime(filter_date_from)
    if dt_from:
        qs = qs.filter(start_time__gte=dt_from)

    dt_to = _parse_datetime(filter_date_to)
    if dt_to:
        qs = qs.filter(start_time__lte=dt_to)

    if filter_search:
        qs = qs.filter(
            Q(status__icontains=filter_search) |
            Q(trigger_by__icontains=filter_search)
        )

    ## paginate
    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    ## build filter_query for pagination links
    filter_query = urlencode({k: v for k, v in {
        'status': filter_status,
        'trigger': filter_trigger,
        'date_from': filter_date_from,
        'date_to': filter_date_to,
        'search': filter_search,
    }.items() if v})

    return render(request, 'workflows/flow_run_history.html', {
        'nav_active': 'workflows',
        'flow': flow,
        'runs': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
        'filter_query': filter_query,
        'filter_status': filter_status,
        'filter_trigger': filter_trigger,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'filter_search': filter_search,
    })


@require_permission('workflows', 'run')
def run_history_all(request):
    """Show global run history across all workflows."""

    ## base queryset
    qs = WfRunHistory.objects.all().order_by('-start_time')

    ## apply filters
    filter_workflow = request.GET.get('workflow', '')
    filter_status = request.GET.get('status', '')
    filter_trigger = request.GET.get('trigger', '')
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')
    filter_search = request.GET.get('search', '')

    if filter_workflow:
        qs = qs.filter(flow_name=filter_workflow)

    if filter_status:
        qs = qs.filter(status=filter_status)

    if filter_trigger == 'job':
        qs = qs.filter(trigger_by__startswith='job:')
    elif filter_trigger == 'manual':
        qs = qs.exclude(trigger_by__startswith='job:')

    dt_from = _parse_datetime(filter_date_from)
    if dt_from:
        qs = qs.filter(start_time__gte=dt_from)

    dt_to = _parse_datetime(filter_date_to)
    if dt_to:
        qs = qs.filter(start_time__lte=dt_to)

    if filter_search:
        qs = qs.filter(
            Q(flow_name__icontains=filter_search) |
            Q(status__icontains=filter_search) |
            Q(trigger_by__icontains=filter_search)
        )

    ## paginate
    try:
        per_page = min(max(int(request.GET.get('per_page', 20)), 10), 2000)
    except (ValueError, TypeError):
        per_page = 20
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    ## get all workflow names for filter dropdown (not just those with runs)
    workflow_names = list(
        WfFlow.objects.filter(deleted=False)
        .values_list('flow_name', flat=True)
        .order_by('flow_name')
    )

    ## build filter_query for pagination links
    filter_query = urlencode({k: v for k, v in {
        'workflow': filter_workflow,
        'status': filter_status,
        'trigger': filter_trigger,
        'date_from': filter_date_from,
        'date_to': filter_date_to,
        'search': filter_search,
    }.items() if v})

    return render(request, 'workflows/run_history_all.html', {
        'nav_active': 'run_history',
        'runs': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_count': paginator.count,
        'filter_query': filter_query,
        'workflow_names': workflow_names,
        'filter_workflow': filter_workflow,
        'filter_status': filter_status,
        'filter_trigger': filter_trigger,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
        'filter_search': filter_search,
    })


## ---------------------------------------------------------
## Version History Views
## ---------------------------------------------------------

@require_permission('workflows', 'view')
def flow_versions(request, flow_name):
    """Show version history for a workflow."""

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp
    versions = WfVersion.get_history(WfVersion.TYPE_FLOW, flow_name)

    return render(request, 'workflows/flow_versions.html', {
        'nav_active': 'workflows',
        'flow': flow,
        'versions': versions,
    })


@require_permission('workflows', 'view')
def flow_version_detail(request, flow_name, version_id):
    """Show a specific version's content."""

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp
    version = get_object_or_404(
        WfVersion, pk=version_id,
        type=WfVersion.TYPE_FLOW,
        target_name=flow_name,
    )

    ## pretty-print JSON content
    try:
        data = json.loads(version.content)
        content = json.dumps(data, indent=4, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        content = version.content

    return render(request, 'workflows/flow_version_detail.html', {
        'nav_active': 'workflows',
        'flow': flow,
        'version': version,
        'content': content,
    })


@require_permission('workflows', 'view')
def flow_version_diff(request, flow_name):
    """Compare two flow versions side by side."""

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp

    v1_id = request.GET.get('v1')
    v2_id = request.GET.get('v2')

    v1 = get_object_or_404(
        WfVersion, pk=v1_id,
        type=WfVersion.TYPE_FLOW,
        target_name=flow_name,
    )
    v2 = get_object_or_404(
        WfVersion, pk=v2_id,
        type=WfVersion.TYPE_FLOW,
        target_name=flow_name,
    )

    ## pretty-print JSON for better diffing
    try:
        v1_content = json.dumps(json.loads(v1.content), indent=4, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        v1_content = v1.content

    try:
        v2_content = json.dumps(json.loads(v2.content), indent=4, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        v2_content = v2.content

    return render(request, 'workflows/flow_version_diff.html', {
        'nav_active': 'workflows',
        'flow': flow,
        'v1': v1,
        'v2': v2,
        'v1_content': v1_content,
        'v2_content': v2_content,
    })


@require_permission('workflows', 'edit')
def flow_version_restore(request, flow_name, version_id):
    """Restore a workflow to a previous version."""

    if request.method != 'POST':
        return redirect('workflows:flow_versions', flow_name=flow_name)

    flow, err_resp = _get_flow_or_not_found(request, flow_name)
    if err_resp:
        return err_resp
    version = get_object_or_404(
        WfVersion, pk=version_id,
        type=WfVersion.TYPE_FLOW,
        target_name=flow_name,
    )

    ## parse the stored version content
    try:
        data = json.loads(version.content)
        procedures = data.get('procedures', [])
        variables = data.get('variables', {})
    except (json.JSONDecodeError, TypeError) as e:
        messages.error(request, 'Failed to parse version content: %s' % e)
        return redirect('workflows:flow_versions', flow_name=flow_name)

    ## save current state as a new version before restoring
    try:
        current_data = flow.get_procedures()
        current_content = json.dumps(current_data, indent=4, ensure_ascii=False)
        WfVersion.create_version(
            type=WfVersion.TYPE_FLOW,
            target_name=flow_name,
            content=current_content,
            changed_by=request.user.username,
        )
    except Exception:
        pass

    ## call API to update with old procedures
    client = get_api_client()
    result = client.update_flow(flow_name, procedures, variables=variables)

    if result.get('status'):
        ## save restored version AFTER the update so runlog can find it
        try:
            WfVersion.create_version(
                type=WfVersion.TYPE_FLOW,
                target_name=flow_name,
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
                target_type='flow',
                target_name=flow_name,
                detail={
                    'request': {
                        'method': request.method,
                        'path': request.path,
                        'headers': _get_request_headers(request),
                        'body': {'restored_version': version.version},
                    },
                    'response': {
                        'status_code': 200,
                        'location': '/workflows/%s/versions/' % flow_name,
                    },
                },
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        messages.success(request, 'Workflow "%s" restored to version %d.' % (flow_name, version.version))
    else:
        messages.error(request, 'Failed to restore workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_versions', flow_name=flow_name)
