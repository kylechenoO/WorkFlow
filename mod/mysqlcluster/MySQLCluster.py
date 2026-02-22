"""
MySQL Cluster Workflow Procedure Module

This module defines the MySQLCluster procedure class used by the workflow
engine for MySQL cluster operations with automatic failover. It accepts a
list of MySQL node configurations and transparently fails over to the next
available node on connection errors. Data operations are delegated to the
MySQL module via composition to avoid code duplication.

The MySQLBase instance (with its active connection) is stored in the workflow
context under a reserved key so it persists across procedure steps.

Responsibilities:
    - Connect to a list of MySQL nodes with automatic failover
    - Retry operations on the next node when a connection error occurs
    - Delegate query, insert, update, insertWithUK operations to MySQL base class
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import pymysql
from pymysql import OperationalError, InterfaceError

## import private pkgs
from mysql.MySQL import MySQL as MySQLBase


class MySQLCluster(object):
    """
    MySQL cluster connection manager with automatic failover.

    Accepts a list of node configs and connects to the first available node.
    On operation failure due to connection errors, transparently retries on
    the next available node in the list.

    The MySQLBase instance (with active connection) is stored in the workflow
    context under '__mysqlcluster_mysql__' so it persists across steps.
    """

    ## context keys
    _CTX_MYSQL = '__mysqlcluster_mysql__'
    _CTX_NODES = '__mysqlcluster_nodes__'
    _CTX_IDX   = '__mysqlcluster_idx__'
    _CTX_RETRY = '__mysqlcluster_retry__'

    def __init__(self, logger: object) -> None:
        """
        Initialize the MySQLCluster manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _get_mysql(self, context: dict) -> MySQLBase:
        """Return the MySQLBase instance from context, or a new one."""
        inst = context.get(self._CTX_MYSQL)
        if inst is None:
            inst = MySQLBase(self.logger)
            context[self._CTX_MYSQL] = inst
        return inst

    def _try_connect(self, context: dict, node: dict) -> bool:
        """
        Attempt to connect to a single node.

        Args:
            context (dict): Workflow context
            node (dict): Node config with host, port, username, password, database, charset

        Returns:
            bool: True if connection succeeded
        """

        result = self._get_mysql(context).connect(context, node)
        return result.get('status', False)

    ## def connect(self, nodes, retry_on_error) -> dict:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Connect to the first available MySQL node in the list.

        Tries each node in order until a successful connection is established.

        Args:
            nodes (list): List of node config dicts, each with:
                          host, port, username, password, database, charset
            retry_on_error (bool): Enable auto-failover on operation errors (default: True)

        Returns:
            dict: Connection status and connected node host
        """

        ## load args
        nodes = cfgs['nodes']
        retry_on_error = cfgs.get('retry_on_error', True)

        ## debug prt
        self.logger.debug({'mysqlcluster.node_count': len(nodes)})
        self.logger.debug({'mysqlcluster.retry_on_error': retry_on_error})

        try:
            ## store nodes and reset index in context
            context[self._CTX_NODES] = nodes
            context[self._CTX_IDX] = 0
            context[self._CTX_RETRY] = retry_on_error

            ## reset mysql instance for fresh connection
            context[self._CTX_MYSQL] = MySQLBase(self.logger)

            ## try each node in order
            for idx, node in enumerate(nodes):
                host = node.get('host', 'unknown')
                self.logger.info({'status': 'Trying MySQL node %s: %s' % (idx, host)})

                if self._try_connect(context, node):
                    context[self._CTX_IDX] = idx
                    self.logger.info({'status': 'Connected to MySQL cluster node %s: %s' % (idx, host)})
                    return {
                        'status': True,
                        'connected_node': host
                    }

                self.logger.error({'status': 'Failed to connect to MySQL node %s: %s' % (idx, host)})

            ## all nodes exhausted
            self.logger.error({'status': 'All MySQL cluster nodes unreachable'})
            return {
                'status': False,
                'connected_node': ''
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting to MySQL cluster: %s' % (e)})
            return {
                'status': False,
                'connected_node': ''
            }

    def _failover(self, context: dict) -> bool:
        """
        Attempt to failover to the next available node.

        Args:
            context (dict): Workflow context

        Returns:
            bool: True if a new node was connected successfully
        """

        nodes = context.get(self._CTX_NODES, [])
        node_idx = context.get(self._CTX_IDX, 0)

        start_idx = node_idx + 1
        for idx in range(start_idx, len(nodes)):
            node = nodes[idx]
            host = node.get('host', 'unknown')
            self.logger.info({'status': 'Failover: trying MySQL node %s: %s' % (idx, host)})

            ## reset mysql instance for fresh connection
            context[self._CTX_MYSQL] = MySQLBase(self.logger)

            if self._try_connect(context, node):
                context[self._CTX_IDX] = idx
                self.logger.info({'status': 'Failover succeeded: connected to MySQL node %s: %s' % (idx, host)})
                return True

            self.logger.error({'status': 'Failover: failed to connect to MySQL node %s: %s' % (idx, host)})

        self.logger.error({'status': 'Failover: all MySQL cluster nodes exhausted'})
        return False

    def _is_connection_error(self, e: Exception) -> bool:
        """
        Check if an exception is a connection-related error.

        Args:
            e (Exception): The caught exception

        Returns:
            bool: True if this is a connection error that warrants failover
        """

        return isinstance(e, (OperationalError, InterfaceError))

    ## def disconnect(self) -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the active MySQL connection.

        This method is safe to call multiple times.
        """

        result = self._get_mysql(context).disconnect(context, cfgs)

        ## clean up cluster context keys
        context[self._CTX_MYSQL] = None
        context[self._CTX_NODES] = None
        context[self._CTX_IDX] = None
        context[self._CTX_RETRY] = None

        return result

    ## def query(self, sql) -> dict:
    def query(self, context: dict, cfgs: dict) -> dict:
        """
        Execute a SELECT query and return results as dictionaries.

        Args:
            sql (str): SQL query string

        Returns:
            dict: Query results
        """

        ## debug prt
        self.logger.debug({'mysqlcluster.op': 'query'})

        retry_on_error = context.get(self._CTX_RETRY, True)

        try:
            result = self._get_mysql(context).query(context, cfgs)

            ## attempt failover if connection error
            if not result.get('status') and retry_on_error and context.get(self._CTX_NODES):
                if self._failover(context):
                    result = self._get_mysql(context).query(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQLCluster query connection error: %s' % (e)})

            if retry_on_error and self._failover(context):
                return self._get_mysql(context).query(context, cfgs)

            return {
                'status': False,
                'result': []
            }

        except Exception as e:
            self.logger.error({'status': 'MySQLCluster query error: %s' % (e)})
            return {
                'status': False,
                'result': []
            }

    ## def insert(self, data, table, cols) -> dict:
    def insert(self, context: dict, cfgs: dict) -> dict:
        """
        Insert multiple rows into a table.

        Args:
            data (ref): Data to insert
            table (str): Target table name
            cols (list): Column list

        Returns:
            dict: Insert status
        """

        ## debug prt
        self.logger.debug({'mysqlcluster.op': 'insert'})

        retry_on_error = context.get(self._CTX_RETRY, True)

        try:
            result = self._get_mysql(context).insert(context, cfgs)

            if not result.get('status') and retry_on_error and context.get(self._CTX_NODES):
                if self._failover(context):
                    result = self._get_mysql(context).insert(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQLCluster insert connection error: %s' % (e)})

            if retry_on_error and self._failover(context):
                return self._get_mysql(context).insert(context, cfgs)

            return {
                'status': False
            }

        except Exception as e:
            self.logger.error({'status': 'MySQLCluster insert error: %s' % (e)})
            return {
                'status': False
            }

    ## def update(self, data, table, cols, where) -> dict:
    def update(self, context: dict, cfgs: dict) -> dict:
        """
        Update records in a table using a WHERE clause.

        Args:
            data (ref): Update data
            table (str): Target table name
            cols (list): Column list
            where (str): WHERE clause

        Returns:
            dict: Update status
        """

        ## debug prt
        self.logger.debug({'mysqlcluster.op': 'update'})

        retry_on_error = context.get(self._CTX_RETRY, True)

        try:
            result = self._get_mysql(context).update(context, cfgs)

            if not result.get('status') and retry_on_error and context.get(self._CTX_NODES):
                if self._failover(context):
                    result = self._get_mysql(context).update(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQLCluster update connection error: %s' % (e)})

            if retry_on_error and self._failover(context):
                return self._get_mysql(context).update(context, cfgs)

            return {
                'status': False
            }

        except Exception as e:
            self.logger.error({'status': 'MySQLCluster update error: %s' % (e)})
            return {
                'status': False
            }

    ## def insertWithUK(self, data, table, cols, uk_cols) -> dict:
    def insertWithUK(self, context: dict, cfgs: dict) -> dict:
        """
        Insert with duplicate key update (upsert).

        Args:
            data (ref): Data to upsert
            table (str): Target table name
            cols (list): Column list
            uk_cols (list): Unique key column list

        Returns:
            dict: Insert/update status
        """

        ## debug prt
        self.logger.debug({'mysqlcluster.op': 'insertWithUK'})

        retry_on_error = context.get(self._CTX_RETRY, True)

        try:
            result = self._get_mysql(context).insertWithUK(context, cfgs)

            if not result.get('status') and retry_on_error and context.get(self._CTX_NODES):
                if self._failover(context):
                    result = self._get_mysql(context).insertWithUK(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQLCluster insertWithUK connection error: %s' % (e)})

            if retry_on_error and self._failover(context):
                return self._get_mysql(context).insertWithUK(context, cfgs)

            return {
                'status': False
            }

        except Exception as e:
            self.logger.error({'status': 'MySQLCluster insertWithUK error: %s' % (e)})
            return {
                'status': False
            }
