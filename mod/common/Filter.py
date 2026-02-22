"""
Filter Workflow Procedure Module

This module defines the Filter procedure class used by the workflow
engine for dict list filtering and transformation operations. The class
methods are invoked dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Filter rows by conditions with multiple operators
    - Select, rename, or drop columns
    - Sort data by one or more columns
    - Remove duplicate rows
    - Slice data with offset and count
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import pandas as pd

class Filter(object):
    """
    Dict list filtering and transformation manager.

    Responsibilities:
        - Filter rows by conditions
        - Select, rename, or drop columns
        - Sort by columns
        - Remove duplicates
        - Slice with offset and count
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the Filter manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    ## def filter(self, data: list, conditions: list) -> dict:
    def filter(self, context: dict, cfgs: dict) -> dict:
        """
        Filter rows by conditions. All conditions are evaluated with AND logic.

        Args:
            data (ref): List of dicts to filter
            conditions (list): List of condition dicts, each with col, op, value (default: [])

        Supported operators:
            eq, ne, gt, gte, lt, lte, in, not_in, contains, not_contains

        Returns:
            dict: Filtered data with count
        """

        ## load args
        data = cfgs['data']
        conditions = cfgs['conditions']

        ## debug prt
        self.logger.debug({'filter.input_count': len(data)})
        self.logger.debug({'filter.conditions': conditions})

        try:
            ## validate data
            if not data:
                self.logger.error({'status': 'Error: data list is empty'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## build operator map
            ops = {
                'eq': lambda a, b: a == b,
                'ne': lambda a, b: a != b,
                'gt': lambda a, b: a > b,
                'gte': lambda a, b: a >= b,
                'lt': lambda a, b: a < b,
                'lte': lambda a, b: a <= b,
                'in': lambda a, b: a in b,
                'not_in': lambda a, b: a not in b,
                'contains': lambda a, b: b in str(a),
                'not_contains': lambda a, b: b not in str(a),
            }

            ## filter rows - all conditions must match (AND logic)
            result = []
            for row in data:
                match = True
                for cond in conditions:
                    col = cond['col']
                    op = cond['op']
                    value = cond['value']

                    if op not in ops:
                        self.logger.error({'status': 'Error: unsupported operator %s' % (op)})
                        return {
                            'status': False,
                            'data': [],
                            'count': 0
                        }

                    if not ops[op](row.get(col), value):
                        match = False
                        break

                if match:
                    result.append(row)

            self.logger.info({'status': 'Filtered %s rows to %s rows' % (len(data), len(result))})
            return {
                'status': True,
                'data': result,
                'count': len(result)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error filtering data: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

    ## def select(self, data: list, cols: list, rename: dict, drop: list) -> dict:
    def select(self, context: dict, cfgs: dict) -> dict:
        """
        Select, rename, or drop columns from a list of dicts.

        Args:
            data (ref): List of dicts
            cols (list): Optional columns to keep (default: [])
            rename (dict): Optional column rename mapping (default: {})
            drop (list): Optional columns to remove (default: [])

        Returns:
            dict: Transformed data with count
        """

        ## load args
        data = cfgs['data']
        cols = cfgs.get('cols', None)
        rename = cfgs.get('rename', None)
        drop = cfgs.get('drop', None)

        ## debug prt
        self.logger.debug({'filter.input_count': len(data)})
        self.logger.debug({'filter.cols': cols})
        self.logger.debug({'filter.rename': rename})
        self.logger.debug({'filter.drop': drop})

        try:
            ## validate data
            if not data:
                self.logger.error({'status': 'Error: data list is empty'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## select columns (whitelist)
            if cols:
                result = []
                for row in data:
                    new_row = {}
                    for col in cols:
                        if col in row:
                            new_row[col] = row[col]
                    result.append(new_row)

            ## rename columns
            elif rename:
                result = []
                for row in data:
                    new_row = {}
                    for key, value in row.items():
                        if key in rename:
                            new_row[rename[key]] = value
                        else:
                            new_row[key] = value
                    result.append(new_row)

            ## drop columns
            elif drop:
                result = []
                for row in data:
                    new_row = {}
                    for key, value in row.items():
                        if key not in drop:
                            new_row[key] = value
                    result.append(new_row)

            ## no operation specified
            else:
                result = data

            self.logger.info({'status': 'Selected %s rows' % (len(result))})
            return {
                'status': True,
                'data': result,
                'count': len(result)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error selecting columns: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

    ## def sort(self, data: list, by: str, ascending: bool) -> dict:
    def sort(self, context: dict, cfgs: dict) -> dict:
        """
        Sort a list of dicts by one or more columns.

        Args:
            data (ref): List of dicts
            by (str): Column name to sort by
            ascending (bool): Optional sort direction (default: true)

        Returns:
            dict: Sorted data with count
        """

        ## load args
        data = cfgs['data']
        by = cfgs['by']
        ascending = cfgs.get('ascending', True)

        ## debug prt
        self.logger.debug({'filter.input_count': len(data)})
        self.logger.debug({'filter.sort_by': by})
        self.logger.debug({'filter.ascending': ascending})

        try:
            ## validate data
            if not data:
                self.logger.error({'status': 'Error: data list is empty'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## use pandas for multi-key sort support
            df = pd.DataFrame(data)
            df = df.sort_values(by=by, ascending=ascending)
            result = df.to_dict(orient='records')

            self.logger.info({'status': 'Sorted %s rows by %s' % (len(result), by)})
            return {
                'status': True,
                'data': result,
                'count': len(result)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error sorting data: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

    ## def dedup(self, data: list, cols: list) -> dict:
    def dedup(self, context: dict, cfgs: dict) -> dict:
        """
        Remove duplicate rows from a list of dicts.

        Args:
            data (ref): List of dicts
            cols (list): Optional columns to check for duplicates (default: [])

        Returns:
            dict: Deduplicated data with count
        """

        ## load args
        data = cfgs['data']
        cols = cfgs.get('cols', None)

        ## debug prt
        self.logger.debug({'filter.input_count': len(data)})
        self.logger.debug({'filter.dedup_cols': cols})

        try:
            ## validate data
            if not data:
                self.logger.error({'status': 'Error: data list is empty'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## deduplicate using seen set
            seen = set()
            result = []
            for row in data:
                if cols:
                    ## build key from specified columns
                    key = tuple(row.get(col) for col in cols)
                else:
                    ## build key from all columns
                    key = tuple(sorted(row.items()))

                if key not in seen:
                    seen.add(key)
                    result.append(row)

            self.logger.info({'status': 'Deduplicated %s rows to %s rows' % (len(data), len(result))})
            return {
                'status': True,
                'data': result,
                'count': len(result)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error deduplicating data: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

    ## def limit(self, data: list, count: int, offset: int) -> dict:
    def limit(self, context: dict, cfgs: dict) -> dict:
        """
        Slice a list of dicts with offset and count.

        Args:
            data (ref): List of dicts
            count (int): Optional number of rows to return (default: 10)
            offset (int): Optional starting offset (default: 0)

        Returns:
            dict: Sliced data with count
        """

        ## load args
        data = cfgs['data']
        count = int(cfgs['count'])
        offset = int(cfgs.get('offset', 0))

        ## debug prt
        self.logger.debug({'filter.input_count': len(data)})
        self.logger.debug({'filter.limit_count': count})
        self.logger.debug({'filter.limit_offset': offset})

        try:
            ## validate data
            if not data:
                self.logger.error({'status': 'Error: data list is empty'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## slice data
            result = data[offset:offset + count]

            self.logger.info({'status': 'Limited %s rows to %s rows (offset=%s)' % (len(data), len(result), offset)})
            return {
                'status': True,
                'data': result,
                'count': len(result)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error limiting data: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }
