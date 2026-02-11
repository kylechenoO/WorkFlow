"""
Elasticsearch Workflow Procedure Module

This module defines the ElasticSearch procedure class used by the workflow
engine for Elasticsearch 8.x operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Establish and close Elasticsearch connections
    - Execute search queries and return structured results
    - Perform document CRUD operations (index, create, update, delete)
    - Batch insert documents with duplicate skipping
    - Manage index lifecycle (create, delete)
    - Health check for cluster status
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
from elasticsearch import Elasticsearch, helpers

class ElasticSearch(object):
    """
    Elasticsearch connection and operation manager.

    Responsibilities:
        - Establish and close Elasticsearch connections
        - Execute search queries and return structured results
        - Perform document CRUD operations
        - Batch insert with duplicate skipping
        - Manage index lifecycle
        - Cluster health check
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the ElasticSearch manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger
        self.con = None

    ## def connect(self, hosts: list, basic_auth: dict, api_key: str, verify_certs: bool, ca_certs: str) -> dict:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Establish a connection to the Elasticsearch cluster.

        Args:
            hosts (list): List of Elasticsearch host URLs
            basic_auth (dict): Optional basic auth credentials with username and password
            api_key (str): Optional API key for authentication
            verify_certs (bool): Whether to verify SSL certificates
            ca_certs (str): Optional file path to CA certificate PEM file

        Returns:
            dict: Connection status
        """

        ## load args
        hosts = cfgs['hosts']
        basic_auth = cfgs.get('basic_auth', None)
        api_key = cfgs.get('api_key', None)
        verify_certs = cfgs.get('verify_certs', False)
        ca_certs = cfgs.get('ca_certs', None)

        ## debug prt
        self.logger.debug({'es.hosts': hosts})
        self.logger.debug({'es.verify_certs': verify_certs})
        self.logger.debug({'es.ca_certs': ca_certs})

        try:
            ## build connection kwargs
            kwargs = {
                'hosts': hosts,
                'verify_certs': verify_certs
            }

            ## set basic auth
            if basic_auth:
                kwargs['basic_auth'] = (basic_auth['username'], basic_auth['password'])

            ## set api key
            if api_key:
                kwargs['api_key'] = api_key

            ## set ca certs
            if ca_certs:
                kwargs['ca_certs'] = ca_certs

            ## connect to es
            self.con = Elasticsearch(**kwargs)

            ## verify connection
            if self.con.ping():
                self.logger.info({'status': 'Successfully connected to Elasticsearch cluster at %s' % (hosts)})
                return {
                    'status': True
                }

            else:
                self.logger.error({'status': 'Failed to connect to Elasticsearch cluster'})
                self.con = None
                return {
                    'status': False
                }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting to Elasticsearch: %s' % (e)})
            self.con = None
            return {
                'status': False
            }

    ## def disconnect(self) -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the active Elasticsearch connection.

        This method is safe to call multiple times.
        """

        try:
            ## disconnect es connection
            if self.con:
                self.con.close()
                self.logger.info({'status': 'Elasticsearch connection closed successfully'})

            self.con = None

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error disconnecting from Elasticsearch: %s' % (e)})

        return {
            'status': True
        }

    ## def health(self) -> dict:
    def health(self, context: dict, cfgs: dict) -> dict:
        """
        Check the health status of the Elasticsearch cluster.

        Returns:
            dict: Cluster health information including status, node count, etc.
        """

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## get cluster health
            health = self.con.cluster.health()

            self.logger.info({'status': 'Cluster health: %s' % (health['status'])})
            return {
                'status': True,
                'result': dict(health)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error checking cluster health: %s' % (e)})
            return {
                'status': False
            }

    ## def search(self, index: str, query: dict, size: int, from_: int, sort: list) -> dict:
    def search(self, context: dict, cfgs: dict) -> dict:
        """
        Execute a search query against an Elasticsearch index.

        Args:
            index (str): Target index name
            query (dict): Elasticsearch query DSL
            size (int): Maximum number of hits to return
            from_ (int): Starting offset for pagination
            sort (list): Sort criteria

        Returns:
            dict: Search results with hits
        """

        ## load args
        index = cfgs['index']
        query = cfgs['query']
        size = cfgs.get('size', 10)
        from_ = cfgs.get('from_', 0)
        sort = cfgs.get('sort', None)

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.query': query})
        self.logger.debug({'es.size': size})
        self.logger.debug({'es.from_': from_})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'result': []
                }

            ## build search kwargs
            kwargs = {
                'index': index,
                'query': query,
                'size': size,
                'from_': from_
            }

            ## set sort
            if sort:
                kwargs['sort'] = sort

            ## execute search
            response = self.con.search(**kwargs)

            ## extract hits
            hits = response['hits']['hits']
            total = response['hits']['total']['value']

            self.logger.info({'status': 'Search executed successfully, returned %s hits (total: %s)' % (len(hits), total)})
            return {
                'status': True,
                'total': total,
                'result': hits
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error executing search: %s' % (e)})
            return {
                'status': False,
                'result': []
            }

    ## def get(self, index: str, id: str) -> dict:
    def get(self, context: dict, cfgs: dict) -> dict:
        """
        Retrieve a single document by its ID.

        Args:
            index (str): Target index name
            id (str): Document ID

        Returns:
            dict: Document data
        """

        ## load args
        index = cfgs['index']
        doc_id = cfgs['id']

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.id': doc_id})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## get document
            response = self.con.get(index=index, id=doc_id)

            self.logger.info({'status': 'Document retrieved successfully: %s' % (doc_id)})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error getting document: %s' % (e)})
            return {
                'status': False
            }

    ## def index(self, index: str, document: dict, id: str) -> dict:
    def index(self, context: dict, cfgs: dict) -> dict:
        """
        Index (insert or replace) a single document.

        If a document with the same ID exists, it will be overwritten.

        Args:
            index (str): Target index name
            document (dict): Document body
            id (str): Optional document ID

        Returns:
            dict: Indexing result
        """

        ## load args
        index = cfgs['index']
        document = cfgs['document']
        doc_id = cfgs.get('id', None)

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.document': document})
        self.logger.debug({'es.id': doc_id})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## build index kwargs
            kwargs = {
                'index': index,
                'document': document
            }

            ## set document id
            if doc_id:
                kwargs['id'] = doc_id

            ## index document
            response = self.con.index(**kwargs)

            self.logger.info({'status': 'Document indexed successfully: %s' % (response['_id'])})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error indexing document: %s' % (e)})
            return {
                'status': False
            }

    ## def create(self, index: str, document: dict, id: str) -> dict:
    def create(self, context: dict, cfgs: dict) -> dict:
        """
        Create a single document. Skips if the document ID already exists.

        Uses the create API which fails if the document already exists,
        preventing accidental overwrites.

        Args:
            index (str): Target index name
            document (dict): Document body
            id (str): Document ID

        Returns:
            dict: Creation result
        """

        ## load args
        index = cfgs['index']
        document = cfgs['document']
        doc_id = cfgs['id']

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.document': document})
        self.logger.debug({'es.id': doc_id})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## create document (fails if id already exists)
            response = self.con.create(index=index, id=doc_id, document=document)

            self.logger.info({'status': 'Document created successfully: %s' % (doc_id)})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error creating document: %s' % (e)})
            return {
                'status': False
            }

    ## def bulk(self, index: str, data: list, id: str) -> dict:
    def bulk(self, context: dict, cfgs: dict) -> dict:
        """
        Batch insert a list of dicts into an Elasticsearch index.

        Uses the create action to skip documents whose ID already exists.
        The id parameter specifies which field in each dict to use as the
        document _id.

        Args:
            index (str): Target index name
            data (list): List of dicts to insert
            id (str): Field name in each dict to use as document _id

        Returns:
            dict: Bulk operation result with success count and errors
        """

        ## load args
        data = cfgs['data']
        index = cfgs['index']
        id_field = cfgs['id']

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.id_field': id_field})
        self.logger.debug({'es.data_count': len(data)})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## check if data is empty
            if not data:
                self.logger.error({'status': 'Error: Data list is empty.'})
                return {
                    'status': False
                }

            ## build actions for helpers.bulk() using 'create' (skip existing _id)
            actions = []
            for doc in data:
                action = {
                    '_op_type': 'create',
                    '_index': index,
                    '_id': doc[id_field],
                    '_source': doc
                }
                actions.append(action)

            self.logger.debug({'status': 'Starting bulk insert for index %s with %s documents' % (index, len(actions))})

            ## execute bulk
            success, errors = helpers.bulk(self.con, actions, raise_on_error=False)

            self.logger.info({'status': 'Bulk insert completed: %s succeeded' % (success)})
            return {
                'status': True,
                'success': success,
                'errors': errors
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error during bulk insert: %s' % (e)})
            return {
                'status': False
            }

    ## def update(self, index: str, id: str, doc: dict) -> dict:
    def update(self, context: dict, cfgs: dict) -> dict:
        """
        Partial update a document by its ID.

        Args:
            index (str): Target index name
            id (str): Document ID
            doc (dict): Partial document with fields to update

        Returns:
            dict: Update result
        """

        ## load args
        index = cfgs['index']
        doc_id = cfgs['id']
        doc = cfgs['doc']

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.id': doc_id})
        self.logger.debug({'es.doc': doc})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## update document
            response = self.con.update(index=index, id=doc_id, doc=doc)

            self.logger.info({'status': 'Document updated successfully: %s' % (doc_id)})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error updating document: %s' % (e)})
            return {
                'status': False
            }

    ## def delete(self, index: str, id: str) -> dict:
    def delete(self, context: dict, cfgs: dict) -> dict:
        """
        Delete a document by its ID.

        Args:
            index (str): Target index name
            id (str): Document ID

        Returns:
            dict: Deletion result
        """

        ## load args
        index = cfgs['index']
        doc_id = cfgs['id']

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.id': doc_id})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## delete document
            response = self.con.delete(index=index, id=doc_id)

            self.logger.info({'status': 'Document deleted successfully: %s' % (doc_id)})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error deleting document: %s' % (e)})
            return {
                'status': False
            }

    ## def createIndex(self, index: str, mappings: dict, settings: dict) -> dict:
    def createIndex(self, context: dict, cfgs: dict) -> dict:
        """
        Create a new Elasticsearch index.

        Args:
            index (str): Index name
            mappings (dict): Optional index mappings
            settings (dict): Optional index settings

        Returns:
            dict: Index creation result
        """

        ## load args
        index = cfgs['index']
        mappings = cfgs.get('mappings', None)
        settings = cfgs.get('settings', None)

        ## debug prt
        self.logger.debug({'es.index': index})
        self.logger.debug({'es.mappings': mappings})
        self.logger.debug({'es.settings': settings})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## build create index kwargs
            kwargs = {
                'index': index
            }

            ## build body
            body = {}

            ## set mappings
            if mappings:
                body['mappings'] = mappings

            ## set settings
            if settings:
                body['settings'] = settings

            ## set body if not empty
            if body:
                kwargs['body'] = body

            ## create index
            response = self.con.indices.create(**kwargs)

            self.logger.info({'status': 'Index created successfully: %s' % (index)})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error creating index: %s' % (e)})
            return {
                'status': False
            }

    ## def deleteIndex(self, index: str) -> dict:
    def deleteIndex(self, context: dict, cfgs: dict) -> dict:
        """
        Delete an Elasticsearch index.

        Args:
            index (str): Index name to delete

        Returns:
            dict: Index deletion result
        """

        ## load args
        index = cfgs['index']

        ## debug prt
        self.logger.debug({'es.index': index})

        try:
            ## check connection
            if not self.con:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## delete index
            response = self.con.indices.delete(index=index)

            self.logger.info({'status': 'Index deleted successfully: %s' % (index)})
            return {
                'status': True,
                'result': dict(response)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error deleting index: %s' % (e)})
            return {
                'status': False
            }

