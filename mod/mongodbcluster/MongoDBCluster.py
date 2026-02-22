"""
MongoDB Cluster Workflow Procedure Module

This module defines the MongoDBCluster procedure class used by the workflow
engine for MongoDB cluster operations with automatic failover. It accepts a
list of MongoDB node configurations and transparently fails over to the next
available node on connection errors. Data operations are delegated to the
MongoDB module via composition to avoid code duplication.

Responsibilities:
    - Connect to a list of MongoDB nodes with automatic failover
    - Retry operations on the next node when a connection error occurs
    - Delegate find, insert, update, delete, count, aggregate to MongoDB base class
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

## import private pkgs
from mongodb.MongoDB import MongoDB as MongoDBBase


class MongoDBCluster(object):
    """
    MongoDB cluster connection manager with automatic failover.

    Accepts a list of node configs and connects to the first available node.
    On operation failure due to connection errors, transparently retries on
    the next available node in the list.
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the MongoDBCluster manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger
        self._nodes = []
        self._node_idx = 0
        self._retry_on_error = True
        self._mongo = MongoDBBase(self.logger)

    def _try_connect(self, context: dict, node: dict) -> bool:
        """
        Attempt to connect to a single MongoDB node.

        Args:
            context (dict): Workflow context (connection stored here)
            node (dict): Node config with host, port, username, password, database, etc.

        Returns:
            bool: True if connection succeeded
        """

        result = self._mongo.connect(context, node)
        return result.get('status', False)

    ## def connect(self, nodes, retry_on_error) -> dict:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Connect to the first available MongoDB node in the list.

        Tries each node in order until a successful connection is established.

        Args:
            nodes (list): List of node config dicts, each with:
                          host, port, username, password, database
                          (plus optional tls, tls_ca_file, etc.)
            retry_on_error (bool): Enable auto-failover on operation errors (default: True)

        Returns:
            dict: Connection status and connected node host
        """

        ## load args
        nodes = cfgs['nodes']
        retry_on_error = cfgs.get('retry_on_error', True)

        ## debug prt
        self.logger.debug({'mongodbcluster.node_count': len(nodes)})
        self.logger.debug({'mongodbcluster.retry_on_error': retry_on_error})

        try:
            ## store nodes and reset state
            self._nodes = nodes
            self._node_idx = 0
            self._retry_on_error = retry_on_error

            ## try each node in order
            for idx, node in enumerate(nodes):
                host = node.get('host', 'unknown')
                self.logger.info({'status': 'Trying MongoDB node %s: %s' % (idx, host)})

                if self._try_connect(context, node):
                    self._node_idx = idx
                    self.logger.info({'status': 'Connected to MongoDB cluster node %s: %s' % (idx, host)})
                    return {
                        'status': True,
                        'connected_node': host
                    }

                self.logger.error({'status': 'Failed to connect to MongoDB node %s: %s' % (idx, host)})

            ## all nodes exhausted
            self.logger.error({'status': 'All MongoDB cluster nodes unreachable'})
            return {
                'status': False,
                'connected_node': ''
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting to MongoDB cluster: %s' % (e)})
            return {
                'status': False,
                'connected_node': ''
            }

    def _failover(self, context: dict) -> bool:
        """
        Attempt to failover to the next available MongoDB node.

        Args:
            context (dict): Workflow context (connection stored here)

        Returns:
            bool: True if a new node was connected successfully
        """

        start_idx = self._node_idx + 1
        for idx in range(start_idx, len(self._nodes)):
            node = self._nodes[idx]
            host = node.get('host', 'unknown')
            self.logger.info({'status': 'Failover: trying MongoDB node %s: %s' % (idx, host)})

            if self._try_connect(context, node):
                self._node_idx = idx
                self.logger.info({'status': 'Failover succeeded: connected to MongoDB node %s: %s' % (idx, host)})
                return True

            self.logger.error({'status': 'Failover: failed to connect to MongoDB node %s: %s' % (idx, host)})

        self.logger.error({'status': 'Failover: all MongoDB cluster nodes exhausted'})
        return False

    def _is_connection_error(self, e: Exception) -> bool:
        """
        Check if an exception is a MongoDB connection-related error.

        Args:
            e (Exception): The caught exception

        Returns:
            bool: True if this is a connection error that warrants failover
        """

        return isinstance(e, (ConnectionFailure, ServerSelectionTimeoutError))

    def _with_failover(self, context: dict, op_name: str, operation, empty_result: dict) -> dict:
        """
        Execute an operation with automatic failover on connection errors.

        Args:
            context (dict): Workflow context (passed to failover reconnect)
            op_name (str): Operation name for logging
            operation (callable): Zero-arg callable that runs the operation
            empty_result (dict): Result to return when all retries fail

        Returns:
            dict: Operation result
        """

        try:
            result = operation()

            if not result.get('status') and self._retry_on_error and self._nodes:
                if self._failover(context):
                    result = operation()

            return result

        ## error handling
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error({'status': 'MongoDBCluster %s connection error: %s' % (op_name, e)})

            if self._retry_on_error and self._failover(context):
                return operation()

            return empty_result

        except Exception as e:
            self.logger.error({'status': 'MongoDBCluster %s error: %s' % (op_name, e)})
            return empty_result

    ## def disconnect(self) -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the active MongoDB connection.

        This method is safe to call multiple times.
        """

        return self._mongo.disconnect(context, cfgs)

    ## def find(self, collection, query, projection, sort, limit, skip) -> dict:
    def find(self, context: dict, cfgs: dict) -> dict:
        """
        Query documents from a collection.

        Args:
            collection (str): Collection name
            query (dict): MongoDB query filter (default: {})
            projection (dict): Optional fields to include/exclude
            sort (list): Optional list of [field, direction] pairs
            limit (int): Optional max documents to return
            skip (int): Optional number of documents to skip

        Returns:
            dict: Query results with data list and count
        """

        self.logger.debug({'mongodbcluster.op': 'find'})
        return self._with_failover(context, 'find', lambda: self._mongo.find(context, cfgs), {'status': False, 'data': [], 'count': 0})

    ## def findOne(self, collection, query) -> dict:
    def findOne(self, context: dict, cfgs: dict) -> dict:
        """
        Retrieve a single document matching the query.

        Args:
            collection (str): Collection name
            query (dict): MongoDB query filter (default: {})

        Returns:
            dict: Single document or None
        """

        self.logger.debug({'mongodbcluster.op': 'findOne'})
        return self._with_failover(context, 'findOne', lambda: self._mongo.findOne(context, cfgs), {'status': False, 'data': None})

    ## def insert(self, collection, data) -> dict:
    def insert(self, context: dict, cfgs: dict) -> dict:
        """
        Insert one or more documents into a collection.

        Args:
            collection (str): Collection name
            data (dict or list): Single document or list of documents

        Returns:
            dict: Insertion result
        """

        self.logger.debug({'mongodbcluster.op': 'insert'})
        return self._with_failover(context, 'insert', lambda: self._mongo.insert(context, cfgs), {'status': False, 'inserted_count': 0, 'inserted_ids': []})

    ## def update(self, collection, query, update, multi) -> dict:
    def update(self, context: dict, cfgs: dict) -> dict:
        """
        Update documents matching a query.

        Args:
            collection (str): Collection name
            query (dict): MongoDB filter query
            update (dict): Update document (e.g. {"$set": {"field": "value"}})
            multi (bool): Update all matching documents (default: False)

        Returns:
            dict: Update result
        """

        self.logger.debug({'mongodbcluster.op': 'update'})
        return self._with_failover(context, 'update', lambda: self._mongo.update(context, cfgs), {'status': False, 'matched': 0, 'modified': 0})

    ## def delete(self, collection, query, multi) -> dict:
    def delete(self, context: dict, cfgs: dict) -> dict:
        """
        Delete documents matching a query.

        Args:
            collection (str): Collection name
            query (dict): MongoDB filter query
            multi (bool): Delete all matching (default: False)

        Returns:
            dict: Deletion result
        """

        self.logger.debug({'mongodbcluster.op': 'delete'})
        return self._with_failover(context, 'delete', lambda: self._mongo.delete(context, cfgs), {'status': False, 'deleted': 0})

    ## def count(self, collection, query) -> dict:
    def count(self, context: dict, cfgs: dict) -> dict:
        """
        Count documents matching a query.

        Args:
            collection (str): Collection name
            query (dict): MongoDB filter query (default: {})

        Returns:
            dict: Document count
        """

        self.logger.debug({'mongodbcluster.op': 'count'})
        return self._with_failover(context, 'count', lambda: self._mongo.count(context, cfgs), {'status': False, 'count': 0})

    ## def aggregate(self, collection, pipeline) -> dict:
    def aggregate(self, context: dict, cfgs: dict) -> dict:
        """
        Run an aggregation pipeline on a collection.

        Args:
            collection (str): Collection name
            pipeline (list): MongoDB aggregation pipeline stages

        Returns:
            dict: Aggregation results
        """

        self.logger.debug({'mongodbcluster.op': 'aggregate'})
        return self._with_failover(context, 'aggregate', lambda: self._mongo.aggregate(context, cfgs), {'status': False, 'data': [], 'count': 0})
