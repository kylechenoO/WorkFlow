"""
DataTransformer Workflow Procedure Module

This module defines the DataTransformer procedure class used by the workflow
engine for converting between list-of-dicts and pandas DataFrame formats.
The class methods are invoked dynamically by the Flow engine during workflow
execution.

Responsibilities:
    - Convert list of dicts to pandas DataFrame
    - Convert pandas DataFrame to list of dicts
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import pandas as pd

class DataTransformer(object):
    """
    Data format conversion manager for workflow procedures.

    Responsibilities:
        - Convert list of dicts to pandas DataFrame
        - Convert pandas DataFrame to list of dicts
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the DataTransformer manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def dicts2df(self, context: dict, cfgs: dict) -> dict:
        """
        Convert a list of dicts to a pandas DataFrame.

        Args:
            data (ref): List of dicts to convert

        Returns:
            dict: Result with DataFrame in data key
        """

        data = cfgs['data']
        df = pd.DataFrame(data)
        return {
            'status': True,
            'data': df
        }

    def df2dicts(self, context: dict, cfgs: dict) -> dict:
        """
        Convert a pandas DataFrame to a list of dicts.

        Args:
            data (ref): Pandas DataFrame to convert

        Returns:
            dict: Result with list of dicts in data key
        """

        df = cfgs['data']
        data = df.to_dict(orient = 'records')
        return {
            'status': True,
            'data': data
        }
