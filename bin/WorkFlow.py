"""
WorkFlow Execution Engine

This module provides the main entry point for initializing and executing
workflow definitions stored in a backend database. It is responsible for:

- Loading configuration
- Initializing logging
- Managing database connections
- Creating and executing workflow instances
- Exposing a CLI interface for workflow execution and inspection
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
import argparse

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

    def run(self, flow_name) -> bool:
        """
        Execute a workflow by name.

        Args:
            flow_name (str): Name of the workflow to execute

        Returns:
            bool: True if execution was triggered successfully
        """

        ## exec specify flow
        context = {}
        flow = self.FlowObj.execFlow(flow_name, context)
        return True

    def list_flows(self) -> bool:
        """
        List all available workflows.

        Returns:
            bool: True after workflows are logged
        """

        flows = self.FlowObj.getFlows()
        self.logger.info({'flows': flows})
        return True

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
        "-l", "--list",
        action="store_true",
        help="List all available workflows"
    )
    group.add_argument(
        "-f", "--flow",
        dest="flow_name",
        help="Execute workflow by flow name"
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

    """
    ## gen 2 sample flows for test
    """
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
                    'msg': '@step1.msg',
                }
            },
        ]
    }
    flow = wfObj.FlowObj.genFlow(flow_name, flow_procedures)
    wfObj.FlowObj.createFlow(flow)

    flow_name = 'flow2'
    flow_procedures = {
        'procedures': [
            {
                'name': 'step1',
                'mod': 'common.Kt',
                'method': 'prt1',
                'params': {
                    'msg': 'hello 2',
                }
            },
            {
                'name': 'step2',
                'mod': 'common.Kt',
                'method': 'prt2',
                'params': {
                    'msg': '@step1.msg',
                }
            },
        ]
    }
    flow = wfObj.FlowObj.genFlow(flow_name, flow_procedures)
    wfObj.FlowObj.createFlow(flow)

    if args.flow_name:
        wfObj.run(flow_name = args.flow_name)
        sys.exit(0)

    if args.list:
        wfObj.list_flows()
        sys.exit(0)

if __name__ == "__main__":
    """
    Command-line entry point.

    This function is executed only when the module is run as a
    script. It will not be executed when the module is imported.
    """

    main()

