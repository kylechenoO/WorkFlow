"""
MySQL Workflow Procedure Module

This module defines the MySQL procedure class used by the workflow
engine for database operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Establish and close MySQL database connections
    - Execute queries and return structured results
    - Perform insert, update, and upsert operations
    - Handle transactions safely with rollback support
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import time
import pymysql
import pandas as pd
from pymysql import Error, OperationalError, InterfaceError
from logging import Logger

## import private pkgs
from common.DataTransformer import DataTransformer

class MySQL(object):
    """
    MySQL database connection and operation manager.

    Responsibilities:
        - Establish and close database connections
        - Execute queries and return structured results
        - Perform insert, update, and upsert operations
        - Handle transactions safely with rollback support
    """

    ## context keys
    _CTX_CON = '__mysql_con__'
    _CTX_CUR = '__mysql_cur__'

    ## cluster context keys
    _CTX_CLUSTER_HOSTS       = '__mysql_cluster_hosts__'
    _CTX_CLUSTER_IDX         = '__mysql_cluster_idx__'
    _CTX_CLUSTER_RETRY       = '__mysql_cluster_retry__'
    _CTX_CLUSTER_TIMEOUT     = '__mysql_cluster_timeout__'
    _CTX_CLUSTER_RETRY_COUNT = '__mysql_cluster_retry_count__'
    _CTX_CLUSTER_DELAY       = '__mysql_cluster_delay__'

    def __init__(self, logger: object) -> None:
        """
        Initialize the MySQL manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _get_con(self, context: dict):
        """Return the MySQL connection from context, or None."""
        return context.get(self._CTX_CON)

    def _get_cur(self, context: dict):
        """Return the MySQL cursor from context, or None."""
        return context.get(self._CTX_CUR)

    ## def connect(self, host: str, port: str, username: str, password: str, database: str, charset: str) -> bool:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Establish a connection to the MySQL database.

        Args:
            host (str): MySQL server hostname or IP
            port (int): Optional MySQL server port (default: 3306)
            username (str): Database username
            password (str): Database password
            database (str): Database name
            charset (str): Optional character encoding (default: "utf8mb4")

        Returns:
            bool: True if connection is successful, False otherwise
        """

        ## load args
        host = cfgs['host']
        port = cfgs['port']
        username = cfgs['username']
        password = cfgs['password']
        database = cfgs['database']
        charset = cfgs['charset']
        connect_timeout = cfgs.get('connect_timeout', None)

        ## debug prt
        self.logger.debug({'db.host': host})
        self.logger.debug({'db.port': port})
        self.logger.debug({'db.username': username})
        self.logger.debug({'db.database': database})
        self.logger.debug({'db.charset': charset})

        try:
            ## build connection kwargs
            kwargs = {
                'host': host,
                'port': int(port),
                'user': username,
                'password': password,
                'database': database,
                'charset': charset
            }

            ## set connect timeout if provided (convert ms to seconds)
            if connect_timeout is not None:
                kwargs['connect_timeout'] = int(connect_timeout / 1000) or 1

            ## connect to db
            con = pymysql.connect(**kwargs)

            ## gen cursor
            if con.open:
                cur = con.cursor()
                context[self._CTX_CON] = con
                context[self._CTX_CUR] = cur
                self.logger.info({'status': 'Successfully connected to MySQL database %s at %s:%s' % (database, host, port)})
                return {
                    'status': True
                }

            else:
                self.logger.error({'status': 'Failed to connect to MySQL database'})
                context[self._CTX_CON] = None
                context[self._CTX_CUR] = None
                return {
                    'status': False
                }

        ## error handling
        except Error as e:
            self.logger.error({'status': "Error connecting to MySQL: %s" % (e)})
            context[self._CTX_CON] = None
            context[self._CTX_CUR] = None
            return {
                'status': False
            }

    ## def disconnect(self) -> None:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the active cursor and database connection.

        This method is safe to call multiple times.
        """

        try:
            ## disconnect cursor
            cur = self._get_cur(context)
            if cur:
                cur.close()
                self.logger.info({'status': 'Cursor closed successfully'})

            ## disconnect db connection
            con = self._get_con(context)
            if con and con.open:
                con.close()
                self.logger.info({'status': 'MySQL connection closed successfully'})

            context[self._CTX_CUR] = None
            context[self._CTX_CON] = None

        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error disconnecting from MySQL: %s' % (e)})

        return {
            'status': True
        }

    ## def showDatabases(self) -> dict:
    def showDatabases(self, context: dict, cfgs: dict) -> dict:
        """
        Retrieve all databases available on the MySQL server.

        Returns:
            list: List of database names, or empty list on error
        """

        try:
            ## check db connection
            cur = self._get_cur(context)
            if not cur:
                self.logger.error({'status': 'Error: No active cursor. Please connect first.'})
                return []

            ## query
            cur.execute("SHOW DATABASES")
            databases = cur.fetchall()

            ## transfer data format
            databases = [row[0] for row in databases] if len(databases) > 0 else []
            self.logger.info({'databases': 'Available Databases:\n%s' % (databases)})
            return {
                'status': True,
                'databases': databases
            }

        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error showing databases: %s' % (e)})
            return {
                'status': False,
                'databases': []
            }

    ## def query(self, SQL: str) -> list:
    def query(self, context: dict, cfgs: dict) -> dict:
        """
        Execute a SELECT query and return results as dictionaries.

        Args:
            SQL (str): SQL query string

        Returns:
            list: List of result rows as dictionaries
        """
        ## load args
        SQL = cfgs['sql']

        try:
            ## check db connection
            cur = self._get_cur(context)
            if not cur:
                self.logger.error({'status': 'Error: No active cursor. Please connect first.'})
                return {
                    'status': False,
                    'result': []
                }

            ## execute query
            cur.execute(SQL)
            results = cur.fetchall()

            ## get column names from cursor description
            if cur.description:
                columns = [desc[0] for desc in cur.description]

            else:
                columns = []

            self.logger.info({'status': 'Query executed successfully, returned %s rows' % (len(results))})

            ## return as list of dicts
            if not results:
                return {
                    'status': True,
                    'result': []
                }

            dict_results = []
            for row in results:
                dict_results.append(dict(zip(columns, row)))

            self.logger.info({'result': 'Returning %s records as dict format' % (len(dict_results))})
            return {
                'status': True,
                'result': dict_results
            }

        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error executing query: %s' % (e)})
            return {
                'status': False,
                'result': []
            }

    ## def insertWithUK(self, data: list, table: str, cols: list, uniq_key: str, batch_size: str) -> bool:
    def insertWithUK(self, context: dict, cfgs: dict) -> dict:
        """
        Insert or update records using a unique key constraint.

        Uses ON DUPLICATE KEY UPDATE and processes data in batches.

        Args:
            data (ref): Input data
            table (str): Target table name
            cols (list): Optional column list (default: [])
            uniq_key (str): Unique key column for ON DUPLICATE KEY UPDATE
            batch_size (int): Optional batch size for inserts (default: 1000)

        Returns:
            bool: True on success, False on failure
        """

        ## load args
        data = cfgs['data']
        table = cfgs['table']
        cols = cfgs['cols']
        uniq_key = cfgs['uniq_key']
        batch_size = int(cfgs['batch_size'])

        ## transfer dicts to df
        DataTransformerObj = DataTransformer(self.logger)
        dicts2df_args = {
            'data': data
        }
        df = DataTransformerObj.dicts2df(context, dicts2df_args)['data']
        try:
            ## validation
            cur = self._get_cur(context)
            con = self._get_con(context)
            if not cur:
                self.logger.error({'status': 'Error: No active cursor. Please connect first.'})
                return {
                    'status': False
                }

            ## check if df is empty
            if df is None or df.empty:
                self.logger.error({'status': 'Error: DataFrame is empty or None.'})
                return {
                    'status': False
                }

            ## check cols
            missing_cols = [col for col in cols if col not in df.columns]
            if missing_cols:
                self.logger.error({'status': 'Error: Columns not found in DataFrame: %s' % (missing_cols)})
                return {
                    'status': False
                }

            ## prepare DataFrame columns for MySQL INSERT
            ## replace NaN with None for proper NULL handling
            df = df.where(pd.notna(df), None)

            ## build SQL components
            columns_str = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))

            ## build UPDATE clause for duplicate key handling
            update_cols = [col for col in cols if col != uniq_key]
            update_parts = ["%s=VALUES(%s)" % (col, col) for col in update_cols]

            ## add update_time to ensure it updates on duplicate key
            update_parts.append("update_time=NOW()")
            update_clause = ', '.join(update_parts)
            total_rows = len(df)
            self.logger.debug({'status': 'Starting insert for table %s with %s rows, batch_size=%s' % (table, total_rows, batch_size)})

            ## process by batch_size
            for start_idx in range(0, total_rows, batch_size):
                end_idx = min(start_idx + batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]
                batch_rows = len(batch_df)

                ## build batch VALUES clause
                batch_placeholders = ', '.join(['(%s)' % placeholders] * batch_rows)

                ## INSERT to specified table with ON DUPLICATE KEY UPDATE
                sql = "INSERT INTO %s (%s) VALUES %s ON DUPLICATE KEY UPDATE %s" % (
                    table, columns_str, batch_placeholders, update_clause
                )

                ## extract values from DataFrame using vectorized operation
                values = batch_df[cols].values.flatten().tolist()

                ## execute batch insert
                cur.execute(sql, values)
                self.logger.debug({'status': 'Processed batch %s-%s (%s rows)' % (start_idx + 1, end_idx, batch_rows)})

            ## commit all batches at once
            con.commit()
            self.logger.debug({'status': 'Successfully committed %s rows to table %s' % (total_rows, table)})
            return {
                'status': True
            }

        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error during insert: %s' % (e)})
            con = self._get_con(context)
            if con:
                con.rollback()
                self.logger.debug({'status': 'Rolled back transaction'})

            return {
                'status': False
            }

    ## def insert(self, data: list, table: str, cols: list) -> bool:
    def insert(self, context: dict, cfgs: dict) -> dict:
        """
        Insert multiple rows into a table in a single SQL statement.

        Args:
            data (ref): Data to insert
            table (str): Target table name
            cols (list): Optional column list (default: [])

        Returns:
            bool: True on success, False on failure
        """

        ## load args
        data = cfgs['data']
        table = cfgs['table']
        cols = cfgs['cols']

        ## transfer dicts to df
        DataTransformerObj = DataTransformer(self.logger)
        dicts2df_args = {
            'data': data
        }
        df = DataTransformerObj.dicts2df(context, dicts2df_args)['data']
        try:
            ## check db connection
            cur = self._get_cur(context)
            con = self._get_con(context)
            if not cur:
                self.logger.error({'status': 'No active cursor.'})
                return {
                    'status': False
                }

            ## check if df is empty
            if df is None or df.empty:
                self.logger.error({'status': 'DataFrame is empty.'})
                return {
                    'status': False
                }

            ## validate columns
            missing = [c for c in cols if c not in df.columns]
            if missing:
                self.logger.error({'status': 'Missing columns: %s' % missing})
                return {
                    'status': False
                }

            ## replace NaN with None
            df = df.where(pd.notna(df), None)

            ## SQL fields
            col_str = ", ".join(f"`{c}`" for c in cols)
            row_placeholder = "(" + ", ".join(["%s"] * len(cols)) + ")"

            ## build multi-row placeholders
            placeholders = ", ".join([row_placeholder] * len(df))

            ## flat list of values
            values = []
            for row in df[cols].itertuples(index=False, name=None):
                values.extend(row)
            sql = f"INSERT INTO `{table}` ({col_str}) VALUES {placeholders}"

            ## execute
            self.logger.debug({'sql': '%s' % (sql)})
            self.logger.debug({'val': '%s' % (values)})
            cur.execute(sql, values)
            con.commit()
            self.logger.debug({'status': 'Inserted %s rows into %s in one SQL statement' % (len(df), table)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            con = self._get_con(context)
            if con:
                con.rollback()

            self.logger.error({'status': 'Error: %s' % (e)})
            return {
                'status': False
            }

    ## def update(self, data: dict, table: str, cols: list, where: str) -> bool:
    def update(self, context: dict, cfgs: dict) -> dict:
        """
        Update records in a table using a WHERE clause.

        Args:
            data (ref): Update data
            table (str): Target table name
            cols (list): Optional column list (default: [])
            where (str): WHERE clause

        Returns:
            bool: True on success, False on failure
        """

        ## load args
        data = cfgs['data']
        table = cfgs['table']
        cols = cfgs['cols']
        where = cfgs['where']

        ## transfer dicts to df
        DataTransformerObj = DataTransformer(self.logger)
        dicts2df_args = {
            'data': data
        }
        df = DataTransformerObj.dicts2df(context, dicts2df_args)['data']
        try:
            ## check db connection
            cur = self._get_cur(context)
            con = self._get_con(context)
            if not cur:
                self.logger.error({'status': 'No active cursor.'})
                return {
                    'status': False
                }

            ## check if df is empty
            if df is None or df.empty:
                self.logger.error({'status': 'DataFrame is empty.'})
                return {
                    'status': False
                }

            ## only use first row for update
            row = df.iloc[0].where(pd.notna(df.iloc[0]), None)

            ## validate columns
            missing_cols = [c for c in cols if c not in df.columns]
            if missing_cols:
                self.logger.error({'status': 'Missing update columns: %s' % missing_cols})
                return {
                    'status': False
                }

            ## SET part
            set_clause = ", ".join(f"`{c}`=%s" for c in cols)
            values = [row[c] for c in cols]

            sql = f"UPDATE `{table}` SET {set_clause} WHERE {where}"

            ## debug
            self.logger.debug({'sql': '%s' % (sql)})
            self.logger.debug({'val': '%s' % (values)})

            ## execute
            cur.execute(sql, values)
            con.commit()
            self.logger.debug({'status': 'Updated %s rows in %s' % (cur.rowcount, table)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            con = self._get_con(context)
            if con:
                con.rollback()

            self.logger.error({'status': 'Error: %s' % (e)})
            return {
                'status': False
            }

    ## ---------------------------------------------------------------
    ## Cluster methods — multi-node connection with automatic failover
    ## ---------------------------------------------------------------

    def _cluster_try_connect(self, context: dict, node: dict) -> bool:
        """
        Attempt to connect to a single MySQL node.

        Args:
            context (dict): Workflow context (connection stored here)
            node (dict): Node config with host, port, username, password, database, charset

        Returns:
            bool: True if connection succeeded
        """

        ## inject timeout from cluster context if available
        timeout_ms = context.get(self._CTX_CLUSTER_TIMEOUT, None)
        if timeout_ms is not None:
            node = dict(node)
            node['connect_timeout'] = timeout_ms

        result = self.connect(context, node)
        return result.get('status', False)

    def _cluster_failover(self, context: dict) -> bool:
        """
        Attempt to failover to the next available MySQL node with wrap-around retry.

        Tries all nodes starting from the current index + 1, wrapping around.
        Repeats for retry_count rounds with retry_delay sleep between rounds.

        Args:
            context (dict): Workflow context

        Returns:
            bool: True if a new node was connected successfully
        """

        hosts = context.get(self._CTX_CLUSTER_HOSTS, [])
        node_idx = context.get(self._CTX_CLUSTER_IDX, 0)
        retry_count = context.get(self._CTX_CLUSTER_RETRY_COUNT, 3)
        retry_delay = context.get(self._CTX_CLUSTER_DELAY, 1.0)
        num_hosts = len(hosts)

        if num_hosts == 0:
            self.logger.error({'status': 'Failover: no MySQL cluster hosts configured'})
            return False

        for round_num in range(retry_count):
            self.logger.info({'status': 'Failover round %s/%s for MySQL cluster' % (round_num + 1, retry_count)})

            ## sleep between rounds (not before the first)
            if round_num > 0:
                self.logger.debug({'status': 'Failover: sleeping %ss before round %s' % (retry_delay, round_num + 1)})
                time.sleep(retry_delay)

            ## try all nodes in wrap-around order starting from current + 1
            for offset in range(1, num_hosts + 1):
                idx = (node_idx + offset) % num_hosts
                node = hosts[idx]
                host = node.get('host', 'unknown')
                self.logger.info({'status': 'Failover: trying MySQL node %s: %s' % (idx, host)})

                ## reset connection for fresh attempt
                context[self._CTX_CON] = None
                context[self._CTX_CUR] = None

                if self._cluster_try_connect(context, node):
                    context[self._CTX_CLUSTER_IDX] = idx
                    self.logger.info({'status': 'Failover succeeded: connected to MySQL node %s: %s' % (idx, host)})
                    return True

                self.logger.error({'status': 'Failover: failed to connect to MySQL node %s: %s' % (idx, host)})

        self.logger.error({'status': 'Failover: all MySQL cluster nodes exhausted after %s rounds' % (retry_count)})
        return False

    def _cluster_is_connection_error(self, e: Exception) -> bool:
        """
        Check if an exception is a MySQL connection-related error.

        Args:
            e (Exception): The caught exception

        Returns:
            bool: True if this is a connection error that warrants failover
        """

        return isinstance(e, (OperationalError, InterfaceError))

    ## def cluster_connect(self, hosts, retry_on_error, timeout, retry_count, retry_delay) -> dict:
    def cluster_connect(self, context: dict, cfgs: dict) -> dict:
        """
        Connect to the first available MySQL node in a cluster.

        Tries each node in order until a successful connection is established.

        Args:
            hosts (list): List of node config dicts, each with:
                          host, port, username, password, database, charset
            retry_on_error (bool): Enable auto-failover on operation errors (default: True)
            timeout (int): Connection timeout per node in milliseconds (default: 5000)
            retry_count (int): Number of full rounds through all nodes on failover (default: 3)
            retry_delay (float): Sleep in seconds between failover rounds (default: 1.0)

        Returns:
            dict: Connection status and connected node host
        """

        ## load args
        hosts = cfgs['hosts']
        retry_on_error = cfgs.get('retry_on_error', True)
        timeout = int(cfgs.get('timeout', 5000))
        retry_count = int(cfgs.get('retry_count', 3))
        retry_delay = float(cfgs.get('retry_delay', 1.0))

        ## debug prt
        self.logger.debug({'mysql_cluster.host_count': len(hosts)})
        self.logger.debug({'mysql_cluster.retry_on_error': retry_on_error})
        self.logger.debug({'mysql_cluster.timeout': timeout})
        self.logger.debug({'mysql_cluster.retry_count': retry_count})
        self.logger.debug({'mysql_cluster.retry_delay': retry_delay})

        try:
            ## store hosts and reset state in context
            context[self._CTX_CLUSTER_HOSTS] = hosts
            context[self._CTX_CLUSTER_IDX] = 0
            context[self._CTX_CLUSTER_RETRY] = retry_on_error
            context[self._CTX_CLUSTER_TIMEOUT] = timeout
            context[self._CTX_CLUSTER_RETRY_COUNT] = retry_count
            context[self._CTX_CLUSTER_DELAY] = retry_delay

            ## reset connection
            context[self._CTX_CON] = None
            context[self._CTX_CUR] = None

            ## try each host in order
            for idx, node in enumerate(hosts):
                host = node.get('host', 'unknown')
                self.logger.info({'status': 'Trying MySQL node %s: %s' % (idx, host)})

                if self._cluster_try_connect(context, node):
                    context[self._CTX_CLUSTER_IDX] = idx
                    self.logger.info({'status': 'Connected to MySQL cluster node %s: %s' % (idx, host)})
                    return {
                        'status': True,
                        'connected_node': host
                    }

                self.logger.error({'status': 'Failed to connect to MySQL node %s: %s' % (idx, host)})

            ## all hosts exhausted
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

    ## def cluster_disconnect(self) -> dict:
    def cluster_disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the active MySQL cluster connection and clean up context.

        This method is safe to call multiple times.
        """

        result = self.disconnect(context, cfgs)

        ## clean up cluster context keys
        context[self._CTX_CLUSTER_HOSTS] = None
        context[self._CTX_CLUSTER_IDX] = None
        context[self._CTX_CLUSTER_RETRY] = None
        context[self._CTX_CLUSTER_TIMEOUT] = None
        context[self._CTX_CLUSTER_RETRY_COUNT] = None
        context[self._CTX_CLUSTER_DELAY] = None

        return result

    ## def cluster_query(self, sql) -> dict:
    def cluster_query(self, context: dict, cfgs: dict) -> dict:
        """
        Execute a SELECT query with automatic cluster failover.

        Args:
            sql (str): SQL query string

        Returns:
            dict: Query results
        """

        ## debug prt
        self.logger.debug({'mysql_cluster.op': 'query'})

        retry_on_error = context.get(self._CTX_CLUSTER_RETRY, True)

        try:
            result = self.query(context, cfgs)

            ## attempt failover if query failed
            if not result.get('status') and retry_on_error and context.get(self._CTX_CLUSTER_HOSTS):
                if self._cluster_failover(context):
                    result = self.query(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQL cluster query connection error: %s' % (e)})

            if retry_on_error and self._cluster_failover(context):
                return self.query(context, cfgs)

            return {
                'status': False,
                'result': []
            }

        except Exception as e:
            self.logger.error({'status': 'MySQL cluster query error: %s' % (e)})
            return {
                'status': False,
                'result': []
            }

    ## def cluster_insert(self, data, table, cols) -> dict:
    def cluster_insert(self, context: dict, cfgs: dict) -> dict:
        """
        Insert rows with automatic cluster failover.

        Args:
            data (ref): Data to insert
            table (str): Target table name
            cols (list): Column list

        Returns:
            dict: Insert status
        """

        ## debug prt
        self.logger.debug({'mysql_cluster.op': 'insert'})

        retry_on_error = context.get(self._CTX_CLUSTER_RETRY, True)

        try:
            result = self.insert(context, cfgs)

            if not result.get('status') and retry_on_error and context.get(self._CTX_CLUSTER_HOSTS):
                if self._cluster_failover(context):
                    result = self.insert(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQL cluster insert connection error: %s' % (e)})

            if retry_on_error and self._cluster_failover(context):
                return self.insert(context, cfgs)

            return {
                'status': False
            }

        except Exception as e:
            self.logger.error({'status': 'MySQL cluster insert error: %s' % (e)})
            return {
                'status': False
            }

    ## def cluster_update(self, data, table, cols, where) -> dict:
    def cluster_update(self, context: dict, cfgs: dict) -> dict:
        """
        Update records with automatic cluster failover.

        Args:
            data (ref): Update data
            table (str): Target table name
            cols (list): Column list
            where (str): WHERE clause

        Returns:
            dict: Update status
        """

        ## debug prt
        self.logger.debug({'mysql_cluster.op': 'update'})

        retry_on_error = context.get(self._CTX_CLUSTER_RETRY, True)

        try:
            result = self.update(context, cfgs)

            if not result.get('status') and retry_on_error and context.get(self._CTX_CLUSTER_HOSTS):
                if self._cluster_failover(context):
                    result = self.update(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQL cluster update connection error: %s' % (e)})

            if retry_on_error and self._cluster_failover(context):
                return self.update(context, cfgs)

            return {
                'status': False
            }

        except Exception as e:
            self.logger.error({'status': 'MySQL cluster update error: %s' % (e)})
            return {
                'status': False
            }

    ## def cluster_insertWithUK(self, data, table, cols, uk_cols) -> dict:
    def cluster_insertWithUK(self, context: dict, cfgs: dict) -> dict:
        """
        Insert with duplicate key update (upsert) with automatic cluster failover.

        Args:
            data (ref): Data to upsert
            table (str): Target table name
            cols (list): Column list
            uk_cols (list): Unique key column list

        Returns:
            dict: Insert/update status
        """

        ## debug prt
        self.logger.debug({'mysql_cluster.op': 'insertWithUK'})

        retry_on_error = context.get(self._CTX_CLUSTER_RETRY, True)

        try:
            result = self.insertWithUK(context, cfgs)

            if not result.get('status') and retry_on_error and context.get(self._CTX_CLUSTER_HOSTS):
                if self._cluster_failover(context):
                    result = self.insertWithUK(context, cfgs)

            return result

        ## error handling
        except (OperationalError, InterfaceError) as e:
            self.logger.error({'status': 'MySQL cluster insertWithUK connection error: %s' % (e)})

            if retry_on_error and self._cluster_failover(context):
                return self.insertWithUK(context, cfgs)

            return {
                'status': False
            }

        except Exception as e:
            self.logger.error({'status': 'MySQL cluster insertWithUK error: %s' % (e)})
            return {
                'status': False
            }
