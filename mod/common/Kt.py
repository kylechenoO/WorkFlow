"""
Sample Workflow Procedure Module

This module defines a simple procedure class used by the workflow engine
for demonstration and testing purposes. The class methods are invoked
dynamically by the Flow engine during workflow execution.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

class Kt(object):
    """
    Example workflow procedure implementation.

    This class provides simple procedure methods that log a message and
    return a structured result. It serves as a reference implementation
    for custom workflow procedure modules.
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the procedure instance.

        Args:
            logger (object): Logger instance provided by the workflow engine
        """

        self.logger = logger
    
    def prt1(self, context: dict, cfgs: dict) -> dict:
        """
        Log a message and return a result payload.

        Args:
            context (dict): Shared workflow execution context
            cfgs (dict): Procedure configuration parameters

        Returns:
            dict: Procedure execution result
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
            cfgs (dict): Procedure configuration parameters

        Returns:
            dict: Procedure execution result
        """

        msg = cfgs['msg']
        self.logger.info({'msg': msg})
        return {
            'status': 0,
            'msg': 'ret from %s' % (msg)
        }

