"""
MySQL Database Access Layer

This module provides a MySQL wrapper class that encapsulates common
database operations, including connection management, querying,
inserts, updates, and batch upserts. It is designed to integrate
with the application's structured logging system.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import pymysql
import pandas as pd
from pymysql import Error
from logging import Logger
from urllib.parse import quote_plus

class MySQL(object):
    """
    MySQL database connection and operation manager.

    Responsibilities:
        - Establish and close database connections
        - Execute queries and return structured results
        - Perform insert, update, and upsert operations
        - Handle transactions safely with rollback support
    """
    
    def __init__(self, logger: object) -> None:
        """
        Initialize the MySQL manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger
        self.con = None
        self.cur = None

    def dicts2df(self, data: dict) -> dict:
        """
        Convert dictionary-based data to a Pandas DataFrame.

        Args:
            data (dict): Input data

        Returns:
            pandas.DataFrame: Converted DataFrame
        """

        df = pd.DataFrame(data)
        return df
    
    def connect(self, host: str, port: str, username: str, password: str, database: str, charset: str) -> bool:
        """
        Establish a connection to the MySQL database.

        Args:
            host (str): MySQL server hostname or IP
            port (str): MySQL server port
            username (str): Database username
            password (str): Database password
            database (str): Database name
            charset (str): Character encoding

        Returns:
            bool: True if connection is successful, False otherwise
        """

        ## debug prt
        self.logger.debug({'db.host': host})
        self.logger.debug({'db.port': port})
        self.logger.debug({'db.username': username})
        self.logger.debug({'db.password': password})
        self.logger.debug({'db.database': database})
        self.logger.debug({'db.charset': charset})

        try:
            ## connect to db
            self.con = pymysql.connect(
                host = host,
                port = int(port),
                user = username,
                password = quote_plus(password),
                database = database,
                charset = charset
            )
            
            ## gen cursor
            if self.con.open:
                self.cur = self.con.cursor()
                self.logger.info({'status': 'Successfully connected to MySQL database %s at %s:%s' % (database, host, port)})
                return True

            else:
                self.logger.error({'status': 'Failed to connect to MySQL database'})
                return False
                
        ## error handling
        except Error as e:
            self.logger.error({'status': "Error connecting to MySQL: %s" % (e)})
            self.con = None
            self.cur = None
            return False

    def disconnect(self) -> None:
        """
        Close the active cursor and database connection.

        This method is safe to call multiple times.
        """

        try:
            ## disconnect cursor
            if self.cur:
                self.cur.close()
                self.logger.info({'status': 'Cursor closed successfully'})

            ## disconnect db connection
            if self.con and self.con.open:
                self.con.close()
                self.logger.info({'status': 'MySQL connection closed successfully'})

            self.cur = None
            self.con = None

        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error disconnecting from MySQL: %s' % (e)})

        return None

    def showDatabases(self) -> dict:
        """
        Retrieve all databases available on the MySQL server.

        Returns:
            list: List of database names, or empty list on error
        """

        try:
            ## check db connection
            if not self.cur:
                self.logger.error({'status': 'Error: No active cursor. Please connect first.'})
                return []

            ## query
            self.cur.execute("SHOW DATABASES")
            databases = self.cur.fetchall()

            ## transfer data format
            databases = [row[0] for row in databases] if len(databases) > 0 else []
            self.logger.info({'databases': 'Available Databases:\n%s" % (data)'})
            return databases

        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error showing databases: %s" % (e)'})
            return []

    def query(self, SQL: str) -> list:
        """
        Execute a SELECT query and return results as dictionaries.

        Args:
            SQL (str): SQL query string

        Returns:
            list: List of result rows as dictionaries
        """

        try:
            ## check db connection
            if not self.cur:
                self.logger.error({'status': 'Error: No active cursor. Please connect first.'})
                return None
            
            ## execute query
            self.cur.execute(SQL)
            results = self.cur.fetchall()
            
            ## get column names from cursor description
            if self.cur.description:
                columns = [desc[0] for desc in self.cur.description]

            else:
                columns = []
            
            self.logger.info({'status': 'Query executed successfully, returned %s rows' % (len(results))})

            ## return as list of dicts
            if not results:
                return []

            dict_results = []
            for row in results:
                dict_results.append(dict(zip(columns, row)))

            self.logger.info({'result': 'Returning %s records as dict format' % (len(dict_results))})
            return dict_results
                
        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error executing query: %s' % (e)})
            return []

    def insertWithUK(self, data: list, table: str, cols: list, uniq_key: str, batch_size: str) -> bool:
        """
        Insert or update records using a unique key constraint.

        Uses ON DUPLICATE KEY UPDATE and processes data in batches.

        Args:
            data (list): Input data
            table (str): Target table name
            cols (list): Column list
            uniq_key (str): Unique key column
            batch_size (int): Batch size for inserts

        Returns:
            bool: True on success, False on failure
        """

        ## transfer dicts to df
        df = self.dicts2df(data)
        try:
            ## validation
            if not self.cur:
                self.logger.error({'status': 'Error: No active cursor. Please connect first.'})
                return False

            ## check if df is empty
            if df is None or df.empty:
                self.logger.error({'status': 'Error: DataFrame is empty or None.'})
                return False

            ## check cols
            missing_cols = [col for col in cols if col not in df.columns]
            if missing_cols:
                self.logger.error({'status': 'Error: Columns not found in DataFrame: %s' % (missing_cols)})
                return False

            ## prepare DataFrame columns for MySQL INSERT
            ## replace NaN with None for proper NULL handling
            df = df.where(pd.notna(df), None)

            ## build SQL components
            columns_str = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))

            ## bild UPDATE clause for duplicate key handling
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
                self.cur.execute(sql, values)
                self.logger.debug({'status': 'Processed batch %s-%s (%s rows)' % (start_idx + 1, end_idx, batch_rows)})
            
            ## commit all batches at once
            self.con.commit()
            self.logger.debug({'status': 'Successfully committed %s rows to table %s' % (total_rows, table)})
            return True
            
        ## error handling
        except Error as e:
            self.logger.error({'status': 'Error during insert: %s' % (e)})
            if self.con:
                self.con.rollback()
                self.logger.debug({'status': 'Rolled back transaction'})

            return False

    def insert(self, data: list, table: str, cols: list) -> bool:
        """
        Insert multiple rows into a table in a single SQL statement.

        Args:
            data (list): Input data
            table (str): Target table
            cols (list): Column list

        Returns:
            bool: True on success, False on failure
        """

        ## transfer dicts to df
        df = self.dicts2df(data)
        try:
            ## check db connection
            if not self.cur:
                self.logger.error({'status': 'No active cursor.'})
                return False
    
            ## check if df is empty
            if df is None or df.empty:
                self.logger.error({'status': 'DataFrame is empty.'})
                return False
    
            ## validate columns
            missing = [c for c in cols if c not in df.columns]
            if missing:
                self.logger.error({'status': 'Missing columns: %s' % missing})
                return False
    
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
            self.cur.execute(sql, values)
            self.con.commit()
            self.logger.debug({'status': 'Inserted %s rows into %s in one SQL statement' % (len(df), table)})
            return True
    
        ## error handling
        except Exception as e:
            if self.con:
                self.con.rollback()
    
            self.logger.error({'status': 'Error: %s' % (e)})
            return False
    

    def update(self, data: dict, table: str, cols: list, where: str) -> bool:
        """
        Update records in a table using a WHERE clause.

        Args:
            data (dict): Update data
            table (str): Target table
            cols (list): Columns to update
            where (str): SQL WHERE condition

        Returns:
            bool: True on success, False on failure
        """

        ## transfer dicts to df
        df = self.dicts2df(data)
        try:
            ## check db connection
            if not self.cur:
                self.logger.error({'status': 'No active cursor.'})
                return False
    
            ## check if df is empty
            if df is None or df.empty:
                self.logger.error({'status': 'DataFrame is empty.'})
                return False
    
            ## only use first row for update
            row = df.iloc[0].where(pd.notna(df.iloc[0]), None)
    
            ## validate columns
            missing_cols = [c for c in cols if c not in df.columns]
            if missing_cols:
                self.logger.error({'status': 'Missing update columns: %s' % missing_cols})
                return False
    
            ## SET part
            set_clause = ", ".join(f"`{c}`=%s" for c in cols)
            values = [row[c] for c in cols]
    
            sql = f"UPDATE `{table}` SET {set_clause} WHERE {where}"
    
            ## debug
            self.logger.debug({'sql': '%s' % (sql)})
            self.logger.debug({'val': '%s' % (values)})
    
            ## execute
            self.cur.execute(sql, values)
            self.con.commit()
            self.logger.debug({'status': 'Updated %s rows in %s' % (self.cur.rowcount, table)})
            return True
    
        ## error handling
        except Exception as e:
            if self.con:
                self.con.rollback()

            self.logger.error({'status': 'Error: %s' % (e)})
            return False
    
