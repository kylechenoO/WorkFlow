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
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import re
import os
import sys
import json
import json5
import argparse
from datetime import datetime

## import flask
from flask import Flask, request, jsonify


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
        self.logger.debug({'db.password': self.config['db']['password']})
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

    def run(self, flow_name) -> dict:
        """
        Execute a workflow by name.

        Args:
            flow_name (str): Name of the workflow to execute

        Returns:
            dict: Execution result with status and context
        """

        ## exec specify flow
        context = {}
        result = self.FlowObj.execFlow(flow_name, context)
        return {
            'status': True,
            'data': context
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
                result = wf.run(name)
                return jsonify(result)
            except Exception as e:
                wf.logger.error({'status': 'Error in API run_flow: %s' % (e)})
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
        port = int(api_config.get('port', 5000))
        debug = api_config.get('debug', False)
        app = wfObj.create_app()
        app.run(host=host, port=port, debug=debug)
        sys.exit(0)


def create_app():
    """
    Application factory for gunicorn.

    Usage:
        gunicorn -w 4 -b 0.0.0.0:5000 'bin.WorkFlow:create_app()'

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
