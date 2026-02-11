"""
Workflows Views

Handles workflow listing, editing (dual-mode editor),
and actions (create, delete, enable, disable, rename, run).
"""

## import buildin pkgs
import json

## import django pkgs
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import WfFlow
from .api_client import WorkflowAPIClient


def get_api_client():
    """Get a WorkflowAPIClient instance."""
    return WorkflowAPIClient()


@login_required
def flow_list(request):
    """List all non-deleted workflows."""

    flows = WfFlow.objects.filter(deleted=False).order_by('flow_name')

    return render(request, 'workflows/flow_list.html', {
        'nav_active': 'workflows',
        'flows': flows,
    })


@login_required
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
        result = client.create_flow(flow_name, procedures)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='create',
                    target_type='flow',
                    target_name=flow_name,
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


@login_required
def flow_edit(request, flow_name):
    """Edit an existing workflow via the dual-mode editor."""

    flow = get_object_or_404(WfFlow, flow_name=flow_name, deleted=False)
    procedures_data = flow.get_procedures()

    if request.method == 'POST':
        procedures_json = request.POST.get('procedures_json', '{}')

        ## parse procedures
        try:
            data = json.loads(procedures_json)
            procedures = data.get('procedures', [])
        except json.JSONDecodeError as e:
            messages.error(request, 'Invalid JSON: %s' % e)
            return render(request, 'workflows/flow_edit.html', {
                'nav_active': 'workflows',
                'is_create': False,
                'flow_name': flow_name,
                'procedures_json': procedures_json,
            })

        ## call API
        client = get_api_client()
        result = client.update_flow(flow_name, procedures)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='update',
                    target_type='flow',
                    target_name=flow_name,
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


@login_required
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
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" deleted.' % flow_name)
        else:
            messages.error(request, 'Failed to delete workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@login_required
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
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" enabled.' % flow_name)
        else:
            messages.error(request, 'Failed to enable workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@login_required
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
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" disabled.' % flow_name)
        else:
            messages.error(request, 'Failed to disable workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@login_required
def flow_run(request, flow_name):
    """Execute a workflow via API."""

    if request.method == 'POST':
        client = get_api_client()
        result = client.run_flow(flow_name)

        if result.get('status'):
            ## log audit
            try:
                from audit.models import AuditLog
                AuditLog.log(
                    user=request.user,
                    action='run',
                    target_type='flow',
                    target_name=flow_name,
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow "%s" executed successfully.' % flow_name)
        else:
            messages.error(request, 'Failed to run workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')


@login_required
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
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass

            messages.success(request, 'Workflow renamed from "%s" to "%s".' % (flow_name, new_name))
        else:
            messages.error(request, 'Failed to rename workflow: %s' % result.get('error', 'Unknown error'))

    return redirect('workflows:flow_list')
