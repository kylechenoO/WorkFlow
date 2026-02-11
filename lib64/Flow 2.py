"""
Workflow Execution Engine

This module defines the Flow class, which is responsible for managing
workflow definitions and executing them step by step. A workflow is
stored as JSON and consists of an ordered list of procedures, each of which
dynamically loads and invokes a module method.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import os
import sys
import json
import importlib
import traceback

class Flow(object):
    """
    Workflow manager and executor.

    Responsibilities:
        - CRUD operations for workflow definitions
        - Dynamic procedures execution
        - Parameter resolution between workflow steps
        - Runtime context propagation
    """

    def __init__(self, logger: object, MySQLObj: object, table: str) -> None:
        """
        Initialize the Flow engine.

        Args:
            logger (object): Logger instance for structured logging
            MySQLObj (object): Database access object
        """

        ## get workpath
        self.logger = logger
        self.MySQLObj = MySQLObj
        self.table = table
        return None

    def resolve_params(self, params: dict, context: dict) -> dict:
        """
        Resolve procedures parameters using the execution context.

        Supported syntax:
            - Literal values: used as-is
            - Escaped literals: @@value -> @value
            - Context reference: @step
            - Context key reference: @step.key

        Args:
            params (dict): Raw procedures parameters
            context (dict): Execution context from previous steps

        Returns:
            dict: Resolved parameters

        Raises:
            KeyError: If referenced context keys do not exist
        """

        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                ## escaped literal: @@xxx -> @xxx
                if v.startswith("@@"):
                    resolved[k] = v[1:]
                    continue
    
                ## reference: @step or @step.key
                if v.startswith("@"):
                    ref = v[1:]
    
                    ## @step.key, reference to a specific key in a step result
                    if "." in ref:
                        step, key = ref.split(".", 1)
    
                        if step not in context:
                            msg = f"Context step not found: {step}"
                            self.logger.error({"msg": msg})
                            raise KeyError(msg)
    
                        if key not in context[step]:
                            msg = f"Key '{key}' not found in context['{step}']"
                            self.logger.error({"msg": msg})
                            raise KeyError(msg)
    
                        resolved[k] = context[step][key]
    
                    # @step, reference to the entire step result
                    else:
                        if ref not in context:
                            msg = f"Context step not found: {ref}"
                            self.logger.error({"msg": msg})
                            raise KeyError(msg)
    
                        resolved[k] = context[ref]
                    continue
            # literal value
            resolved[k] = v
        return resolved

    def getFlows(self) -> list:
        """
        Retrieve all workflows from the database.

        Returns:
            list: List of workflow records
        """

        result = self.MySQLObj.query('SELECT * FROM %s' % (self.table))
        return result

    def getFlow(self, flow_name: str) -> dict:
        """
        Retrieve a single workflow by name.

        Args:
            flow_name (str): Workflow name

        Returns:
            dict: Workflow record or empty list if not found
        """

        result = self.MySQLObj.query('SELECT * FROM %s WHERE flow_name = \'%s\';' % (self.table, flow_name))
        result = result[0] if result != [] else []
        return result

    def genFlow(self, flow_name: str, flow_procedures: dict, enabled: int = 1, deleted: int = 0) -> dict:
        """
        Generate a database-ready workflow record.

        Args:
            flow_name (str): Workflow name
            flow_procedures (dict): Workflow definition
            enabled (int): Enable flag (1 or 0)
            deleted (int): Delete flag (1 or 0)

        Returns:
            dict: Structured data for database insertion
        """

        if isinstance(flow_procedures, dict):
	        flow_procedures_str = json.dumps(flow_procedures, ensure_ascii=False)

        else:
	        flow_procedures_str = str(flow_procedures)
	
        data = {
	        "flow_name": [flow_name],
	        "flow_procedures": [flow_procedures_str],
	        "enabled": [enabled],
	        "deleted": [deleted]
        }
	
        return data
	
    def createFlow(self, flow: dict) -> bool:
        """
        Create a new workflow record.

        Args:
            flow (dict): Workflow data

        Returns:
            bool: True on success
        """

        ret = self.MySQLObj.insert(flow, self.table, [ key for key in flow ])
        return ret

    def updateFlow(self, flow_name: str, flow: dict) -> bool:
        """
        Update an existing workflow.

        Args:
            flow_name (str): Workflow name
            flow (dict): Updated workflow data

        Returns:
            bool: True on success
        """

        ret = self.MySQLObj.update(flow, self.table, [ key for key in flow ], 'flow_name = \"%s\"' % (flow_name))
        return ret

    def renameFlow(self, flow_name_src: str, flow_name_dst: str) -> bool:
        """
        Rename a workflow.

        Args:
            flow_name_src (str): Original workflow name
            flow_name_dst (str): New workflow name

        Returns:
            bool: True on success
        """

        data = {
            "flow_name": [flow_name_dst]
        }
        ret = self.MySQLObj.update(data, self.table, [ key for key in data ], 'flow_name = \"%s\"' % (flow_name_src))
        return ret

    def deleteFlow(self, flow_name: str) -> bool:
        """
        Mark a workflow as deleted.

        Args:
            flow_name (str): Workflow name

        Returns:
            bool: True on success
        """

        data = {
            "deleted": [1]
        }
        ret = self.MySQLObj.update(data, self.table, [ key for key in data ], 'flow_name = \"%s\"' % (flow_name))
        return ret

    def enableFlow(self, flow_name: str) -> bool:
        """
        Enable a workflow.

        Args:
            flow_name (str): Workflow name

        Returns:
            bool: True on success
        """

        data = {
            "enabled": [1]
        }
        ret = self.MySQLObj.update(data, self.table, [ key for key in data ], 'flow_name = \"%s\"' % (flow_name))
        return ret

    def disableFlow(self, flow_name: str) -> bool:
        """
        Disable a workflow.

        Args:
            flow_name (str): Workflow name

        Returns:
            bool: True on success
        """

        data = {
            "enabled": [0]
        }
        ret = self.MySQLObj.update(data, self.table, [ key for key in data ], 'flow_name = \"%s\"' % (flow_name))
        return ret

    def execFlow(self, flow_name: str, context: dict) -> bool:
        """
        Execute a workflow.

        Each procedure is executed sequentially. The result of each procedure is
        stored in the context under the procedures name and may be referenced
        by subsequent procedures.

        Args:
            flow_name (str): Workflow name
            context (dict): Initial execution context

        Returns:
            bool: True if execution completes successfully

        Raises:
            Exception: Re-raised if procedure execution fails
        """

        flow = self.getFlow(flow_name)
        if flow == []:
            self.logger.warning({'status': '%s not existed.' % (flow_name)})
            return False

        flow_procedures = json.loads(flow['flow_procedures'])
        self.logger.info({'flow_name': flow['flow_name']})
        self.logger.info({'flow_procedures': 'flow_procedures'})
        self.logger.info({'enabled': flow['enabled']})
        self.logger.info({'deleted': flow['deleted']})
        for procedure in flow_procedures['procedures']:
            ## load args
            mod = procedure['mod']
            name = procedure['name']
            method = procedure['method']
            params = procedure.get("params", {})

            ## dbg prt
            self.logger.info({'mod': mod})
            self.logger.info({'name': name})
            self.logger.info({'method': method})
            self.logger.info({'params': params})

            ## call func
            try:
                module = importlib.import_module(mod)
                cls_name = mod.split('.')[-1]
                cls = getattr(module, cls_name)
                inst = cls(self.logger)
                func = getattr(inst, method)
    
                params = self.resolve_params(params, context)
                result = func(context, params)
                context[name] = result
    
                self.logger.info({'result': result})

            ## handling exceptions
            except Exception as e:
                self.logger.error(
                    {
                        "flow": flow_name,
                        "procedure": procedure.get("name"),
                        "module": procedure.get("mod"),
                        "method": procedure.get("method"),
                        "error": str(e),
                        "exception": e.__class__.__name__,
                        "traceback": traceback.format_exc()
                    },
                    exc_info = True
                )
                raise

        return True
