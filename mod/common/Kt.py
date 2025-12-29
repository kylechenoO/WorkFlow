"""
Sample Workflow Task Module

This module defines a simple task class used by the workflow engine
for demonstration and testing purposes. The class methods are invoked
dynamically by the Flow engine during workflow execution.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

class Kt(object):
    """
    Example workflow task implementation.

    This class provides simple task methods that log a message and
    return a structured result. It serves as a reference implementation
    for custom workflow task modules.
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the task instance.

        Args:
            logger (object): Logger instance provided by the workflow engine
        """

        self.logger = logger
    
    def prt1(self, context: dict, cfgs: dict) -> dict:
        """
        Log a message and return a result payload.

        Args:
            context (dict): Shared workflow execution context
            cfgs (dict): Task configuration parameters

        Returns:
            dict: Task execution result
        """

        msg = cfgs['msg']
        self.logger.info({'msg': msg})
        return {
            'status': 0,
            'msg': 'ret from %s' % (msg)
        }

    def prt2(self, context: dict, cfgs: dict) -> dict:
        """
        Log a message and return a result payload.

        Args:
            context (dict): Shared workflow execution context
            cfgs (dict): Task configuration parameters

        Returns:
            dict: Task execution result
        """

        msg = cfgs['msg']
        self.logger.info({'msg': msg})
        return {
            'status': 0,
            'msg': 'ret from %s' % (msg)
        }

