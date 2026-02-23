"""
WorkFlow Execution Engine

This module provides the main entry point for initializing and executing
workflow definitions stored in a backend database. It is responsible for:

- Loading configuration
- Initializing logging
- Managing database connections
- Creating and executing workflow instances
- Exposing a CLI interface for workflow execution and inspection
- Exposing a Flask REST API for web service access
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import re
import os
import sys
import json
import json5
import time
import signal
import argparse
import subprocess
from datetime import datetime, timezone

## import flask
from flask import Flask, request, jsonify, send_file


## Resolve project root directory
workpath = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

## Extend Python module search path for project libraries
sys.path.append("%s/lib" % (workpath))
sys.path.append("%s/mod" % (workpath))

## import private pkgs
from Log import Log
from Config import Config
from MySQL import MySQL
from Flow import Flow

class WorkFlow(object):
    """
    Core workflow engine controller.

    This class is responsible for bootstrapping all required subsystems
    (configuration, logging, database, and flow engine) and provides
    methods for executing and managing workflows.

    Lifecycle:
        1. Load configuration
        2. Initialize logging
        3. Establish database connection
        4. Initialize Flow engine
    """
    def __init__(self) -> None:
        """
        Initialize the workflow engine.

        This includes:
        - Loading configuration
        - Initializing the logger
        - Connecting to the database
        - Attaching database-backed logging
        - Creating the Flow engine instance
        """

        ## set private values
        self.config = Config(workpath).config
        self.config['pid'] = os.getpid()
        self.config['pname'] = os.path.basename(__file__)
        self.config['name'] = re.sub(r'\..*$', '', self.config['pname'])

        ## logger init
        self.loggerObj = Log(self.config)
        self.logger = self.loggerObj.logger

        ## debug prt
        self.logger.debug({'db.host': self.config['db']['host']})
        self.logger.debug({'db.port': self.config['db']['port']})
        self.logger.debug({'db.username': self.config['db']['username']})
        self.logger.debug({'db.password': '********'})
        self.logger.debug({'db.database': self.config['db']['database']})
        self.logger.debug({'db.charset': self.config['db']['charset']})

        ## init MySQLObj
        self.MySQLObj = MySQL(self.logger)
        self.MySQLObj.connect(self.config['db']['host'], self.config['db']['port'], self.config['db']['username'], self.config['db']['password'], self.config['db']['database'], self.config['db']['charset'])

        ## prt log to mysql
        self.loggerObj.add_mysql_handler(self.MySQLObj, self.config['log']['table'])

        ## init FlowObj
        self.FlowObj = Flow(self.logger, self.MySQLObj, self.config['flow']['table'])

        ## debug output
        self.logger.debug({'status': 'end'})

    def get_timestamp(self):
        """
        Generate a formatted timestamp string.

        Returns:
            str: Current timestamp in YYYY-MM-DD_HH:MM:SS.mmm format
        """

        now = datetime.now().astimezone()
        ts = now.strftime('%Y-%m-%d_%H:%M:%S.') + f'{now.microsecond // 1000:03d}'
        return ts

    def __destory__(self) -> None:
        """
        Release allocated resources.

        This method disconnects the database connection.
        Intended to be called during shutdown.
        """

        self.MySQLObj.disconnect()

    def runSample(self) -> bool:
        """
        Demonstration method for workflow lifecycle operations.

        This method contains commented examples for:
        - Creating workflows
        - Updating workflows
        - Renaming workflows
        - Enabling / disabling workflows
        - Executing workflows

        Returns:
            bool: Always True
        """

        self.logger.info('[WorkFlow] Start')

        """
        ## flow actions sample
        ## gen a flow
        flow_name = 'flow1'
        flow_procedures = {
            'procedures': [
                {
                    'name': 'step1',
                    'mod': 'common.Kt',
                    'method': 'prt',
                    'params': {
                        'msg': 'hello 1',
                    }
                },
                {
                    'name': 'step2',
                    'mod': 'common.Kt',
                    'method': 'prt',
                    'params': {
                        'msg': '@step1.msg',
                    }
                },
            ]
        }
        flow = self.FlowObj.genFlow(flow_name, flow_procedures)
        self.logger.info({'flow': flow})

        ## create flow
        self.FlowObj.createFlow(flow)

        ## update flow
        flow_name = 'flow1'
        flow_procedures = {
            'procedures': [
                {
                    'name': 'step1',
                    'mod': 'common.Kt',
                    'method': 'prt1',
                    'params': {
                        'msg': 'hello 1',
                    }
                },
                {
                    'name': 'step2',
                    'mod': 'common.Kt',
                    'method': 'prt2',
                    'params': {
                        'msg': 'hello 2',
                    }
                },
            ]
        }
        flow = self.FlowObj.genFlow('flow1', flow_procedures)
        self.FlowObj.updateFlow(flow_name, flow)

        ## rename flow
        flow = self.FlowObj.renameFlow('flow1', 'flow2')

        ## delete flow
        flow_name = 'flow2'
        self.FlowObj.deleteFlow(flow_name)

        ## disable flow
        flow_name = 'flow2'
        self.FlowObj.disableFlow(flow_name)

        ## enable flow
        flow_name = 'flow2'
        self.FlowObj.enableFlow(flow_name)

        ## get all flows
        flows = self.FlowObj.getFlows()
        self.logger.info({'flows': flows})

        ## get specify flow
        flow_name = 'flow2'
        flow = self.FlowObj.getFlow(flow_name)
        self.logger.info({'flow': flow})

        ## exec specify flow
        flow_name = 'flow2'
        context = {}
        flow = self.FlowObj.execFlow(flow_name, context)
        """

        self.logger.info({'status': 'end'})
        return(True)

    def _sanitize_context(self, context):
        """Remove non-serializable internal keys from context for API responses."""
        sanitized = {}
        for k, v in context.items():
            if k.startswith('__') and k.endswith('__'):
                continue
            try:
                json.dumps(v)
                sanitized[k] = v
            except (TypeError, ValueError):
                sanitized[k] = str(v)
        return sanitized

    def run(self, flow_name, trigger_by=None) -> dict:
        """
        Execute a workflow by name and record run history.

        Args:
            flow_name (str): Name of the workflow to execute
            trigger_by (str): Optional — who triggered the run (username or 'api')

        Returns:
            dict: Execution result with status, run_id, and context
        """

        run_id = None
        run_start = time.time()

        try:
            ## insert run history row (status=running)
            self.MySQLObj._ensure_connection()
            now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.') + '%03d' % (datetime.now(timezone.utc).microsecond // 1000)
            insert_sql = (
                "INSERT INTO wf_run_history (flow_name, status, trigger_by, start_time) "
                "VALUES (%s, %s, %s, %s)"
            )
            self.MySQLObj.cur.execute(insert_sql, (flow_name, 'running', trigger_by, now_str))
            self.MySQLObj.con.commit()
            run_id = self.MySQLObj.cur.lastrowid
            self.logger.info({'status': 'Run history created', 'run_id': run_id, 'flow_name': flow_name})

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error creating run history: %s' % (e)})

        ## exec specify flow
        context = {}
        if trigger_by:
            context['__trigger_by__'] = trigger_by
        flow_error = None
        try:
            result = self.FlowObj.execFlow(flow_name, context)

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error executing flow %s: %s' % (flow_name, e)})
            flow_error = str(e)

        ## determine final status
        run_end = time.time()
        duration_ms = int((run_end - run_start) * 1000)
        final_status = 'success'

        if flow_error:
            final_status = 'failed'
        else:
            ## check if any step failed
            steps = context.get('__steps__', [])
            for step in steps:
                if step.get('status') == 'failed':
                    final_status = 'failed'
                    if not flow_error:
                        flow_error = step.get('error')
                    break

        ## update run history with final status
        if run_id:
            try:
                self.MySQLObj._ensure_connection()
                end_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.') + '%03d' % (datetime.now(timezone.utc).microsecond // 1000)
                update_sql = (
                    "UPDATE wf_run_history SET status=%s, end_time=%s, duration_ms=%s, error_msg=%s "
                    "WHERE id=%s"
                )
                self.MySQLObj.cur.execute(update_sql, (final_status, end_str, duration_ms, flow_error, run_id))
                self.MySQLObj.con.commit()

                ## insert step records
                steps = context.get('__steps__', [])
                for step in steps:
                    step_sql = (
                        "INSERT INTO wf_run_step (run_id, step_name, step_order, status, start_time, end_time, duration_ms, result_data, error_msg) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    )
                    try:
                        result_json = json.dumps(step.get('result')) if step.get('result') else None
                    except (TypeError, ValueError):
                        result_json = str(step.get('result'))
                    self.MySQLObj.cur.execute(step_sql, (
                        run_id,
                        step.get('name', ''),
                        step.get('order', 0),
                        step.get('status', 'pending'),
                        step.get('start_time'),
                        step.get('end_time'),
                        step.get('duration_ms'),
                        result_json,
                        step.get('error')
                    ))
                self.MySQLObj.con.commit()
                self.logger.info({'status': 'Run history updated', 'run_id': run_id, 'final_status': final_status, 'steps': len(steps)})

            ## error handling
            except Exception as e:
                self.logger.error({'status': 'Error updating run history: %s' % (e)})

        return {
            'status': final_status == 'success',
            'run_id': run_id,
            'data': self._sanitize_context(context)
        }

    def create_flow(self, flowConf) -> dict:
        """
        Create a workflow.

        Args:
            flowConf (str): JSON5 string containing workflow name and procedures

        Returns:
            dict: Creation result with status
        """
        ## load args
        if isinstance(flowConf, str):
            flowConf = json5.loads(flowConf)

        ## gen a flow
        flow_name = flowConf['name']
        flow_procedures = {'procedures': flowConf['procedures']}
        if 'variables' in flowConf:
            flow_procedures['variables'] = flowConf['variables']
        if '_connections' in flowConf:
            flow_procedures['_connections'] = flowConf['_connections']
        if '_positions' in flowConf:
            flow_procedures['_positions'] = flowConf['_positions']
        flow = self.FlowObj.genFlow(flow_name, flow_procedures)
        self.logger.info({'flow': flow})

        ## create flow
        self.FlowObj.createFlow(flow)
        return {
            'status': True,
            'data': {'flow_name': flow_name}
        }

    def enable_flow(self, flow_name) -> dict:
        """
        Enable a workflow.

        Args:
            flow_name (str): Name of the workflow to enable

        Returns:
            dict: Enable result with status
        """

        self.FlowObj.enableFlow(flow_name)
        return {
            'status': True,
            'data': {'flow_name': flow_name}
        }

    def disable_flow(self, flow_name) -> dict:
        """
        Disable a workflow.

        Args:
            flow_name (str): Name of the workflow to disable

        Returns:
            dict: Disable result with status
        """

        self.FlowObj.disableFlow(flow_name)
        return {
            'status': True,
            'data': {'flow_name': flow_name}
        }

    def rename_flow(self, flow_name_dict) -> dict:
        """
        Rename a workflow.

        Args:
            flow_name_dict (str or dict): JSON5 string or dict with 'current' and 'new' flow names

        Returns:
            dict: Rename result with status
        """

        ## load args
        if isinstance(flow_name_dict, str):
            flow_name_dict = json5.loads(flow_name_dict)
        self.logger.info({'flow_name_dict': flow_name_dict})
        flow_name_current = flow_name_dict['current']
        flow_name_new = flow_name_dict['new']

        ## rename flow
        self.FlowObj.renameFlow(flow_name_current, flow_name_new)
        return {
            'status': True,
            'data': {'flow_name': flow_name_new}
        }

    def delete_flow(self, flow_name) -> dict:
        """
        Delete a workflow (soft delete with timestamp rename).

        Args:
            flow_name (str): Name of the workflow to delete

        Returns:
            dict: Delete result with status
        """

        flow_name_new = '%s_%s_deleted' % (flow_name, self.get_timestamp())
        self.logger.info({'flow_name_new': flow_name_new})
        self.FlowObj.deleteFlow(flow_name)
        self.FlowObj.renameFlow(flow_name, flow_name_new)
        return {
            'status': True,
            'data': {'flow_name': flow_name_new}
        }

    def update_flow(self, flowConf) -> dict:
        """
        Update a workflow.

        Args:
            flowConf (str or dict): JSON5 string or dict containing workflow name and procedures

        Returns:
            dict: Update result with status
        """

        ## load args
        if isinstance(flowConf, str):
            flowConf = json5.loads(flowConf)

        ## gen a flow
        flow_name = flowConf['name']
        flow_procedures = {'procedures': flowConf['procedures']}
        if 'variables' in flowConf:
            flow_procedures['variables'] = flowConf['variables']
        if '_connections' in flowConf:
            flow_procedures['_connections'] = flowConf['_connections']
        if '_positions' in flowConf:
            flow_procedures['_positions'] = flowConf['_positions']
        flow = self.FlowObj.genFlow(flow_name, flow_procedures)
        self.logger.info({'flow': flow})

        ## update flow
        self.FlowObj.updateFlow(flow_name, flow)
        return {
            'status': True,
            'data': {'flow_name': flow_name}
        }

    def get_flow_info(self, flow_name) -> dict:
        """
        Get information of a specific workflow.

        Args:
            flow_name (str): Name of the workflow to retrieve

        Returns:
            dict: Flow info result with status and data
        """

        flow = self.FlowObj.getFlow(flow_name)
        self.logger.info({'flow': flow})
        return {
            'status': True,
            'data': flow
        }

    def list_flows(self) -> dict:
        """
        List all available workflows.

        Returns:
            dict: List result with status and data
        """

        flows = self.FlowObj.getFlows()
        self.logger.info({'flows': flows})
        return {
            'status': True,
            'data': flows
        }

    def create_app(self) -> Flask:
        """
        Create a Flask application with REST API routes.

        Returns:
            Flask: Configured Flask application
        """

        app = Flask(__name__)
        wf = self

        ## GET /flow - list all workflows
        @app.route('/flow', methods=['GET'])
        def api_list_flows():
            try:
                result = wf.list_flows()
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API list_flows: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## GET /flow/<name> - get workflow info
        @app.route('/flow/<name>', methods=['GET'])
        def api_get_flow(name):
            try:
                result = wf.get_flow_info(name)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API get_flow_info: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## POST /flow - create workflow
        @app.route('/flow', methods=['POST'])
        def api_create_flow():
            try:
                body = request.get_json()
                if not body:
                    return jsonify({'status': False, 'error': 'Request body is required'}), 400
                result = wf.create_flow(body)
                return jsonify(result), 201
            except Exception as e:
                wf.logger.error({'status': 'Error in API create_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## PUT /flow/<name> - update workflow
        @app.route('/flow/<name>', methods=['PUT'])
        def api_update_flow(name):
            try:
                body = request.get_json()
                if not body:
                    return jsonify({'status': False, 'error': 'Request body is required'}), 400
                body['name'] = name
                result = wf.update_flow(body)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API update_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## DELETE /flow/<name> - delete workflow (soft)
        @app.route('/flow/<name>', methods=['DELETE'])
        def api_delete_flow(name):
            try:
                result = wf.delete_flow(name)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API delete_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## POST /flow/<name>/run - execute workflow
        @app.route('/flow/<name>/run', methods=['POST'])
        def api_run_flow(name):
            try:
                body = request.get_json(silent=True) or {}
                trigger_by = body.get('trigger_by', 'api')
                result = wf.run(name, trigger_by=trigger_by)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API run_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## GET /flow/<name>/runs - list run history for a workflow
        @app.route('/flow/<name>/runs', methods=['GET'])
        def api_get_run_history(name):
            try:
                limit = request.args.get('limit', 20, type=int)
                wf.MySQLObj._ensure_connection()
                sql = "SELECT id, flow_name, status, trigger_by, start_time, end_time, duration_ms, error_msg FROM wf_run_history WHERE flow_name=%s ORDER BY start_time DESC LIMIT %s"
                wf.MySQLObj.cur.execute(sql, (name, limit))
                rows = wf.MySQLObj.cur.fetchall()
                columns = [desc[0] for desc in wf.MySQLObj.cur.description] if wf.MySQLObj.cur.description else []
                runs = []
                for row in rows:
                    run_dict = dict(zip(columns, row))
                    ## convert datetime to string for JSON
                    for k in ('start_time', 'end_time'):
                        if run_dict.get(k):
                            run_dict[k] = str(run_dict[k])
                    runs.append(run_dict)
                return jsonify({'status': True, 'data': runs})
            except Exception as e:
                wf.logger.error({'status': 'Error in API get_run_history: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## GET /run/<run_id> - get single run detail with steps
        @app.route('/run/<int:run_id>', methods=['GET'])
        def api_get_run_detail(run_id):
            try:
                wf.MySQLObj._ensure_connection()
                ## get run header
                run_sql = "SELECT id, flow_name, status, trigger_by, start_time, end_time, duration_ms, error_msg FROM wf_run_history WHERE id=%s"
                wf.MySQLObj.cur.execute(run_sql, (run_id,))
                run_row = wf.MySQLObj.cur.fetchone()
                if not run_row:
                    return jsonify({'status': False, 'error': 'Run not found'}), 404
                run_cols = [desc[0] for desc in wf.MySQLObj.cur.description]
                run_dict = dict(zip(run_cols, run_row))
                for k in ('start_time', 'end_time'):
                    if run_dict.get(k):
                        run_dict[k] = str(run_dict[k])

                ## get steps
                step_sql = "SELECT id, run_id, step_name, step_order, status, start_time, end_time, duration_ms, result_data, error_msg FROM wf_run_step WHERE run_id=%s ORDER BY step_order"
                wf.MySQLObj.cur.execute(step_sql, (run_id,))
                step_rows = wf.MySQLObj.cur.fetchall()
                step_cols = [desc[0] for desc in wf.MySQLObj.cur.description] if wf.MySQLObj.cur.description else []
                steps = []
                for srow in step_rows:
                    step_dict = dict(zip(step_cols, srow))
                    for k in ('start_time', 'end_time'):
                        if step_dict.get(k):
                            step_dict[k] = str(step_dict[k])
                    ## parse result_data JSON
                    if step_dict.get('result_data') and isinstance(step_dict['result_data'], str):
                        try:
                            step_dict['result_data'] = json.loads(step_dict['result_data'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    steps.append(step_dict)

                run_dict['steps'] = steps
                return jsonify({'status': True, 'data': run_dict})
            except Exception as e:
                wf.logger.error({'status': 'Error in API get_run_detail: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## PUT /flow/<name>/enable - enable workflow
        @app.route('/flow/<name>/enable', methods=['PUT'])
        def api_enable_flow(name):
            try:
                result = wf.enable_flow(name)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API enable_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## PUT /flow/<name>/disable - disable workflow
        @app.route('/flow/<name>/disable', methods=['PUT'])
        def api_disable_flow(name):
            try:
                result = wf.disable_flow(name)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API disable_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## PUT /flow/<name>/rename - rename workflow
        @app.route('/flow/<name>/rename', methods=['PUT'])
        def api_rename_flow(name):
            try:
                body = request.get_json()
                if not body or 'new' not in body:
                    return jsonify({'status': False, 'error': 'Request body with "new" field is required'}), 400
                rename_dict = {'current': name, 'new': body['new']}
                result = wf.rename_flow(rename_dict)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API rename_flow: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## GET /backup - download full backup ZIP
        @app.route('/backup', methods=['GET'])
        def api_backup():
            import hashlib
            import io as _io
            import zipfile as _zipfile
            from datetime import datetime as _dt

            ## authenticate via X-Api-Key header
            plain_key = request.headers.get('X-Api-Key', '')
            if not plain_key:
                return jsonify({'status': False, 'error': 'Authentication required'}), 401

            try:
                key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
                wf.MySQLObj._ensure_connection()
                wf.MySQLObj.cur.execute(
                    "SELECT id, enabled FROM system_api_key WHERE key_hash=%s LIMIT 1",
                    (key_hash,)
                )
                row = wf.MySQLObj.cur.fetchone()
                if not row or not row[1]:
                    return jsonify({'status': False, 'error': 'Invalid or disabled API key'}), 401
                ## update last_used
                wf.MySQLObj.cur.execute(
                    "UPDATE system_api_key SET last_used=NOW() WHERE id=%s",
                    (row[0],)
                )
                wf.MySQLObj.con.commit()
            except Exception as e:
                wf.logger.error({'status': 'Error in API backup auth: %s' % (e)})
                return jsonify({'status': False, 'error': 'Authentication error'}), 500

            ## build backup ZIP
            try:
                buf = _io.BytesIO()
                with _zipfile.ZipFile(buf, 'w', _zipfile.ZIP_DEFLATED) as zf:
                    meta = {
                        'created_at': _dt.utcnow().isoformat() + 'Z',
                        'created_by': 'api',
                        'sections': [],
                    }

                    ## workflows
                    wf.MySQLObj._ensure_connection()
                    wf.MySQLObj.cur.execute(
                        "SELECT flow_name, enabled, flow_procedures FROM wf_flow WHERE deleted=0"
                    )
                    flows = wf.MySQLObj.cur.fetchall()
                    for row in flows:
                        flow_name, enabled, procedures_str = row
                        try:
                            procedures = json.loads(procedures_str) if procedures_str else {}
                        except Exception:
                            procedures = {}
                        data = {'flow_name': flow_name, 'enabled': bool(enabled), 'procedures': procedures}
                        zf.writestr('workflows/%s.json' % flow_name, json.dumps(data, ensure_ascii=False, indent=2))
                    meta['sections'].append('workflows')

                    ## modules
                    mod_root = os.path.join(workpath, 'mod')
                    if os.path.isdir(mod_root):
                        for category in sorted(os.listdir(mod_root)):
                            cat_dir = os.path.join(mod_root, category)
                            if not os.path.isdir(cat_dir):
                                continue
                            for fname in sorted(os.listdir(cat_dir)):
                                if not fname.endswith('.py'):
                                    continue
                                fpath = os.path.join(cat_dir, fname)
                                if os.path.commonpath([os.path.realpath(fpath), os.path.realpath(mod_root)]) != os.path.realpath(mod_root):
                                    continue
                                with open(fpath, 'r', encoding='utf-8') as mf:
                                    zf.writestr('modules/%s/%s' % (category, fname), mf.read())
                    meta['sections'].append('modules')

                    ## settings
                    wf.MySQLObj.cur.execute("SELECT `key`, `value` FROM system_setting")
                    settings_rows = wf.MySQLObj.cur.fetchall()
                    settings_data = {r[0]: r[1] for r in settings_rows} if settings_rows else {}
                    zf.writestr('settings.json', json.dumps(settings_data, ensure_ascii=False, indent=2))
                    meta['sections'].append('settings')

                    ## write metadata
                    zf.writestr('backup.json', json.dumps(meta, ensure_ascii=False, indent=2))

                buf.seek(0)
                filename = 'workflow_backup_%s.zip' % _dt.utcnow().strftime('%Y%m%d_%H%M%S')
                return send_file(buf, mimetype='application/zip',
                                 as_attachment=True, download_name=filename)

            except Exception as e:
                wf.logger.error({'status': 'Error in API backup: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## POST /restore - restore from uploaded backup ZIP
        @app.route('/restore', methods=['POST'])
        def api_restore():
            import hashlib
            import io as _io
            import zipfile as _zipfile

            ## authenticate via X-Api-Key header
            plain_key = request.headers.get('X-Api-Key', '')
            if not plain_key:
                return jsonify({'status': False, 'error': 'Authentication required'}), 401

            try:
                key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
                wf.MySQLObj._ensure_connection()
                wf.MySQLObj.cur.execute(
                    "SELECT id, enabled FROM system_api_key WHERE key_hash=%s LIMIT 1",
                    (key_hash,)
                )
                row = wf.MySQLObj.cur.fetchone()
                if not row or not row[1]:
                    return jsonify({'status': False, 'error': 'Invalid or disabled API key'}), 401
                ## update last_used
                wf.MySQLObj.cur.execute(
                    "UPDATE system_api_key SET last_used=NOW() WHERE id=%s",
                    (row[0],)
                )
                wf.MySQLObj.con.commit()
            except Exception as e:
                wf.logger.error({'status': 'Error in API restore auth: %s' % (e)})
                return jsonify({'status': False, 'error': 'Authentication error'}), 500

            ## restore from uploaded ZIP
            try:
                uploaded = request.files.get('file')
                if not uploaded:
                    return jsonify({'status': False, 'error': 'No file uploaded. Use multipart/form-data with field name "file".'}), 400

                restored = []
                errors   = []

                with _zipfile.ZipFile(_io.BytesIO(uploaded.read())) as zf:
                    ## read metadata
                    try:
                        meta = json.loads(zf.read('backup.json'))
                        sections = meta.get('sections', [])
                    except Exception:
                        return jsonify({'status': False, 'error': 'Invalid backup file: missing backup.json'}), 400

                    ## restore workflows
                    if 'workflows' in sections:
                        try:
                            count = 0
                            for name in zf.namelist():
                                if not name.startswith('workflows/') or not name.endswith('.json'):
                                    continue
                                data = json.loads(zf.read(name))
                                flow_name = data.get('flow_name', '')
                                if not flow_name:
                                    continue
                                procedures = data.get('procedures', {})
                                procedures_str = json.dumps(procedures, ensure_ascii=False)

                                ## check if workflow exists
                                wf.MySQLObj._ensure_connection()
                                wf.MySQLObj.cur.execute(
                                    "SELECT id FROM wf_flow WHERE flow_name=%s AND deleted=0 LIMIT 1",
                                    (flow_name,)
                                )
                                existing = wf.MySQLObj.cur.fetchone()

                                if existing:
                                    wf.MySQLObj.cur.execute(
                                        "UPDATE wf_flow SET flow_procedures=%s, updated_at=NOW() WHERE id=%s",
                                        (procedures_str, existing[0])
                                    )
                                else:
                                    enabled = 1 if data.get('enabled', True) else 0
                                    wf.MySQLObj.cur.execute(
                                        "INSERT INTO wf_flow (flow_name, enabled, flow_procedures, deleted, created_at, updated_at) VALUES (%s, %s, %s, 0, NOW(), NOW())",
                                        (flow_name, enabled, procedures_str)
                                    )
                                wf.MySQLObj.con.commit()
                                count += 1
                            restored.append('workflows (%d)' % count)
                        except Exception as e:
                            errors.append('workflows: %s' % str(e))

                    ## restore modules
                    if 'modules' in sections:
                        try:
                            mod_root = os.path.join(workpath, 'mod')
                            count = 0
                            for name in zf.namelist():
                                if not name.startswith('modules/') or not name.endswith('.py'):
                                    continue
                                parts = name.split('/', 2)
                                if len(parts) != 3:
                                    continue
                                category, fname = parts[1], parts[2]

                                ## path safety
                                target = os.path.realpath(os.path.join(mod_root, category, fname))
                                if os.path.commonpath([target, os.path.realpath(mod_root)]) != os.path.realpath(mod_root):
                                    continue

                                os.makedirs(os.path.join(mod_root, category), exist_ok=True)
                                with open(target, 'w', encoding='utf-8') as mf:
                                    mf.write(zf.read(name).decode('utf-8'))
                                count += 1
                            restored.append('modules (%d files)' % count)
                        except Exception as e:
                            errors.append('modules: %s' % str(e))

                    ## restore settings
                    if 'settings' in sections:
                        try:
                            settings_data = json.loads(zf.read('settings.json'))
                            wf.MySQLObj._ensure_connection()
                            for key, value in settings_data.items():
                                wf.MySQLObj.cur.execute(
                                    "INSERT INTO system_setting (`key`, `value`) VALUES (%s, %s) ON DUPLICATE KEY UPDATE `value`=%s",
                                    (key, value, value)
                                )
                            wf.MySQLObj.con.commit()
                            restored.append('settings')
                        except Exception as e:
                            errors.append('settings: %s' % str(e))

                result = {'status': True, 'restored': restored}
                if errors:
                    result['errors'] = errors
                return jsonify(result), 200

            except _zipfile.BadZipFile:
                return jsonify({'status': False, 'error': 'Uploaded file is not a valid ZIP archive'}), 400
            except Exception as e:
                wf.logger.error({'status': 'Error in API restore: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        ## =============================================================
        ## Service Control Endpoints
        ## =============================================================

        _SVC_DEFS = {
            'backend':  {'port': 5001, 'label': 'Backend (Flask API)'},
            'frontend': {'port': 5002, 'label': 'Frontend (Django UI)'},
        }

        def _api_get_pid(port):
            """Return the PID listening on the given port, or None."""
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

        def _api_stop_svc(port):
            """Stop the process listening on the given port via SIGTERM."""
            pid = _api_get_pid(port)
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                    for _ in range(20):
                        time.sleep(0.1)
                        if _api_get_pid(port) is None:
                            break
                    return True
                except ProcessLookupError:
                    pass
            return False

        def _api_audit_log(action, target_name, detail):
            """Insert audit log entry via raw SQL (no Django ORM available)."""
            try:
                wf.MySQLObj._ensure_connection()
                wf.MySQLObj.cur.execute(
                    "INSERT INTO wf_audit_log (action, target_type, target_name, detail, ip_address)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (action, 'service', target_name,
                     json.dumps(detail, ensure_ascii=False),
                     request.remote_addr)
                )
                wf.MySQLObj.con.commit()
            except Exception:
                pass

        @app.route('/service/<svc>/start', methods=['POST'])
        def api_service_start(svc):
            if svc not in _SVC_DEFS:
                return jsonify({'status': False, 'error': 'Unknown service: %s' % svc}), 400
            svc_info = _SVC_DEFS[svc]
            port = svc_info['port']
            if _api_get_pid(port):
                return jsonify({'status': False, 'error': 'Service is already running on port %d' % port})
            try:
                script_path = os.path.join(workpath, 'bin', 'service.sh')
                subprocess.Popen(
                    ['bash', script_path, 'start', svc],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                _api_audit_log('enable', svc, {
                    'request': {'action': 'start', 'service': svc, 'port': port},
                    'response': {'status': True, 'message': 'Started %s service' % svc_info['label']},
                })
                return jsonify({'status': True, 'running': True, 'message': '%s started' % svc_info['label']})
            except Exception as e:
                wf.logger.error({'status': 'Error in API service_start: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        @app.route('/service/<svc>/stop', methods=['POST'])
        def api_service_stop(svc):
            if svc not in _SVC_DEFS:
                return jsonify({'status': False, 'error': 'Unknown service: %s' % svc}), 400
            svc_info = _SVC_DEFS[svc]
            port = svc_info['port']
            pid = _api_get_pid(port)
            if not pid:
                return jsonify({'status': False, 'error': 'Service is not running'})
            try:
                _api_stop_svc(port)
                _api_audit_log('disable', svc, {
                    'request': {'action': 'stop', 'service': svc, 'port': port, 'pid': pid},
                    'response': {'status': True, 'message': 'Stopped %s service' % svc_info['label']},
                })
                return jsonify({'status': True, 'running': False, 'message': '%s stopped' % svc_info['label']})
            except Exception as e:
                wf.logger.error({'status': 'Error in API service_stop: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        @app.route('/service/<svc>/restart', methods=['POST'])
        def api_service_restart(svc):
            if svc not in _SVC_DEFS:
                return jsonify({'status': False, 'error': 'Unknown service: %s' % svc}), 400
            svc_info = _SVC_DEFS[svc]
            port = svc_info['port']
            try:
                _api_stop_svc(port)
                script_path = os.path.join(workpath, 'bin', 'service.sh')
                subprocess.Popen(
                    ['bash', script_path, 'start', svc],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                _api_audit_log('update', svc, {
                    'request': {'action': 'restart', 'service': svc, 'port': port},
                    'response': {'status': True, 'message': 'Restarted %s service' % svc_info['label']},
                })
                return jsonify({'status': True, 'running': True, 'message': '%s restarted' % svc_info['label']})
            except Exception as e:
                wf.logger.error({'status': 'Error in API service_restart: %s' % (e)})
                return jsonify({'status': False, 'error': str(e)}), 500

        @app.route('/service/<svc>/status', methods=['GET'])
        def api_service_status(svc):
            if svc not in _SVC_DEFS:
                return jsonify({'status': False, 'error': 'Unknown service: %s' % svc}), 400
            svc_info = _SVC_DEFS[svc]
            pid = _api_get_pid(svc_info['port'])
            return jsonify({
                'status': True,
                'running': pid is not None,
                'pid': pid,
            })

        ## =============================================================
        ## CORS Headers (cross-origin from frontend port 5002 to backend port 5001)
        ## =============================================================

        @app.after_request
        def add_cors_headers(response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            return response

        return app


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed CLI arguments
    """

    parser = argparse.ArgumentParser(
        description="Workflow Execution Engine"
    )

    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument(
        "-f", "--flow",
        dest="run_flow",
        help="Execute workflow by flow name"
    )

    group.add_argument(
        "-c", "--create",
        dest="create_flow",
        help="Create workflow by flowConf"
    )

    group.add_argument(
        "-e", "--enable",
        dest="enable_flow",
        help="Enable workflow by flow name"
    )

    group.add_argument(
        "-d", "--disable",
        dest="disable_flow",
        help="Disable workflow by flow name"
    )

    group.add_argument(
        "-r", "--rename",
        dest="rename_flow",
        help="Rename workflow by flow name"
    )

    group.add_argument(
        "-t", "--delete",
        dest="delete_flow",
        help="Delete workflow by flow name"
    )

    group.add_argument(
        "-u", "--update",
        dest="update_flow",
        help="Update workflow by flow name"
    )

    group.add_argument(
        "-i", "--info",
        dest="get_flow_info",
        help="Get spcify workflow info by flow name"
    )

    group.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all available workflows"
    )

    group.add_argument(
        "-s", "--serve",
        action="store_true",
        help="Start REST API server"
    )

    return parser.parse_args()


def main() -> None:
    """
    CLI entry point.

    Initializes the workflow engine and dispatches
    commands based on parsed CLI arguments.
    """

    args = parse_args()
    wfObj = WorkFlow()

    if args.run_flow:
        wfObj.run(flow_name = args.run_flow)
        sys.exit(0)

    if args.create_flow:
        wfObj.create_flow(args.create_flow)
        sys.exit(0)

    if args.enable_flow:
        wfObj.enable_flow(args.enable_flow)
        sys.exit(0)

    if args.disable_flow:
        wfObj.disable_flow(args.disable_flow)
        sys.exit(0)

    if args.delete_flow:
        wfObj.delete_flow(args.delete_flow)
        sys.exit(0)

    if args.rename_flow:
        wfObj.rename_flow(args.rename_flow)
        sys.exit(0)

    if args.update_flow:
        wfObj.update_flow(args.update_flow)
        sys.exit(0)

    if args.get_flow_info:
        wfObj.get_flow_info(args.get_flow_info)
        sys.exit(0)

    if args.list:
        wfObj.list_flows()
        sys.exit(0)

    if args.serve:
        api_config = wfObj.config.get('api', {})
        host = api_config.get('host', '0.0.0.0')
        port = int(api_config.get('port', 5001))
        debug = api_config.get('debug', False)
        app = wfObj.create_app()
        app.run(host=host, port=port, debug=debug)
        sys.exit(0)


def create_app():
    """
    Application factory for gunicorn.

    Usage:
        gunicorn -w 4 -b 0.0.0.0:5001 'bin.WorkFlow:create_app()'

    Returns:
        Flask: Configured Flask application
    """

    wf = WorkFlow()
    app = wf.create_app()
    return app


if __name__ == "__main__":
    """
    Command-line entry point.

    This function is executed only when the module is run as a
    script. It will not be executed when the module is imported.
    """

    main()
