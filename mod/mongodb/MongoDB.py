"""
MongoDB Workflow Procedure Module

This module defines the MongoDB procedure class used by the workflow
engine for MongoDB operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

The MongoDB connection is stored in the workflow context under the
reserved key '__mongodb_con__' and '__mongodb_db__', allowing it to
persist across multiple procedure steps that share the same context.

Responsibilities:
    - Establish and close MongoDB connections with optional TLS/SSL
    - Execute find, findOne, insert, update, delete, count operations
    - Run aggregation pipelines
    - Manage index and collection lifecycle
    - Support TLS cert from local path, URL, or base64 content
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import os
import hashlib
import base64
import urllib.request
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


class MongoDB(object):
    """
    MongoDB connection and operation manager.

    The connection object is stored in the workflow context (not in self)
    so it persists across procedure steps within the same workflow run.

    Responsibilities:
        - Establish and close MongoDB connections with TLS support
        - Execute document CRUD operations
        - Run aggregation pipelines
        - Manage collections and indexes
    """

    ## context keys for connection objects
    _CTX_CON = '__mongodb_con__'
    _CTX_DB  = '__mongodb_db__'

    def __init__(self, logger: object) -> None:
        """
        Initialize the MongoDB manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _get_con(self, context: dict):
        """Return the MongoClient stored in context, or None."""
        return context.get(self._CTX_CON)

    def _get_db(self, context: dict):
        """Return the database handle stored in context, or None."""
        return context.get(self._CTX_DB)

    def _resolve_cert(self, cert_path: str) -> str:
        """
        Resolve a certificate from various sources to a local file path.

        Supported sources:
            - Local file path: used as-is (e.g. /etc/ssl/certs/ca.pem)
            - HTTP/HTTPS URL: downloaded and cached
            - Base64 content: decoded and cached (e.g. base64:LS0tLS1CRUdJTi...)

        Downloaded/decoded certs are cached in /tmp/wf_mongo_certs/.

        Args:
            cert_path (str): Certificate source string

        Returns:
            str: Local file path to the certificate
        """

        ## determine source type
        src = cert_path.strip()

        if src.startswith(('http://', 'https://', 'ftp://')):
            ## url source - download and cache
            self.logger.debug({'cert_source': 'url'})

            cache_dir = '/tmp/wf_mongo_certs'
            os.makedirs(cache_dir, exist_ok=True)
            cache_key = hashlib.sha256(src.encode('utf-8')).hexdigest()
            cache_path = os.path.join(cache_dir, '%s.pem' % cache_key)

            ## reuse cached cert if exists
            if os.path.exists(cache_path):
                self.logger.debug({'cert_cache': 'hit', 'cert_path': cache_path})
                return cache_path

            ## download and cache cert
            try:
                urllib.request.urlretrieve(src, cache_path)
                os.chmod(cache_path, 0o600)
                self.logger.info({'status': 'Certificate downloaded and cached: %s' % cache_path})
                return cache_path

            except Exception as e:
                self.logger.error({'status': 'Error downloading certificate from %s: %s' % (src, e)})
                raise

        elif src.startswith('base64:'):
            ## base64 encoded content
            self.logger.debug({'cert_source': 'base64'})

            cache_dir = '/tmp/wf_mongo_certs'
            os.makedirs(cache_dir, exist_ok=True)
            b64_content = src[7:]
            cache_key = hashlib.sha256(b64_content.encode('utf-8')).hexdigest()
            cache_path = os.path.join(cache_dir, '%s.pem' % cache_key)

            ## reuse cached cert if exists
            if os.path.exists(cache_path):
                self.logger.debug({'cert_cache': 'hit', 'cert_path': cache_path})
                return cache_path

            ## decode and write cert
            try:
                cert_data = base64.b64decode(b64_content)

                fd = os.open(cache_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, 'wb') as f:
                    f.write(cert_data)

                self.logger.info({'status': 'Certificate decoded and cached: %s' % cache_path})
                return cache_path

            except Exception as e:
                self.logger.error({'status': 'Error decoding base64 certificate: %s' % (e)})
                raise

        else:
            ## local file path - use as-is
            self.logger.debug({'cert_source': 'local', 'cert_path': src})
            return src

    ## def connect(self, host, port, username, password, database, ...) -> dict:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Establish a connection to MongoDB.

        Args:
            host (str): MongoDB host (default: "localhost")
            port (int): MongoDB port (default: 27017)
            username (str): Optional username
            password (str): Optional password (never logged)
            database (str): Database name to use
            auth_source (str): Authentication database (default: "admin")
            tls (bool): Enable TLS/SSL (default: False)
            tls_ca_file (str): CA certificate - local path, URL, or base64:... content
            tls_cert_file (str): Client certificate file path
            tls_key_file (str): Client private key file path (never logged)
            tls_allow_invalid_certs (bool): Skip cert validation (default: False)

        Returns:
            dict: Connection status
        """

        ## load args
        host = cfgs.get('host', 'localhost')
        port = int(cfgs.get('port', 27017))
        username = cfgs.get('username', None)
        password = cfgs.get('password', None)
        database = cfgs['database']
        auth_source = cfgs.get('auth_source', 'admin')
        tls = cfgs.get('tls', False)
        tls_ca_file = cfgs.get('tls_ca_file', None)
        tls_cert_file = cfgs.get('tls_cert_file', None)
        tls_key_file = cfgs.get('tls_key_file', None)
        tls_allow_invalid_certs = cfgs.get('tls_allow_invalid_certs', False)

        ## debug prt (never log password or key file)
        self.logger.debug({'mongo.host': host})
        self.logger.debug({'mongo.port': port})
        self.logger.debug({'mongo.username': username})
        self.logger.debug({'mongo.database': database})
        self.logger.debug({'mongo.auth_source': auth_source})
        self.logger.debug({'mongo.tls': tls})

        try:
            ## build connection kwargs
            kwargs = {
                'host': host,
                'port': port,
                'serverSelectionTimeoutMS': 5000
            }

            ## set auth if provided
            if username and password:
                kwargs['username'] = username
                kwargs['password'] = password
                kwargs['authSource'] = auth_source

            ## set tls options
            if tls:
                kwargs['tls'] = True

                if tls_ca_file:
                    kwargs['tlsCAFile'] = self._resolve_cert(tls_ca_file)

                if tls_cert_file:
                    kwargs['tlsCertificateKeyFile'] = self._resolve_cert(tls_cert_file)

                if tls_allow_invalid_certs:
                    kwargs['tlsAllowInvalidCertificates'] = True

            ## connect to mongodb and store in context
            con = MongoClient(**kwargs)

            ## verify connection
            con.admin.command('ping')
            db = con[database]

            context[self._CTX_CON] = con
            context[self._CTX_DB] = db

            self.logger.info({'status': 'Successfully connected to MongoDB at %s:%s' % (host, port)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting to MongoDB: %s' % (e)})
            context[self._CTX_CON] = None
            context[self._CTX_DB] = None
            return {
                'status': False
            }

    ## def disconnect(self) -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the active MongoDB connection.

        This method is safe to call multiple times.
        """

        try:
            ## close connection stored in context
            con = self._get_con(context)
            if con:
                con.close()
                self.logger.info({'status': 'MongoDB connection closed successfully'})

            context[self._CTX_CON] = None
            context[self._CTX_DB] = None

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error disconnecting from MongoDB: %s' % (e)})

        return {
            'status': True
        }

    ## def find(self, collection, query, projection, sort, limit, skip) -> dict:
    def find(self, context: dict, cfgs: dict) -> dict:
        """
        Query documents from a collection.

        Args:
            collection (str): Collection name
            query (dict): MongoDB query filter (default: {})
            projection (dict): Optional fields to include/exclude
            sort (list): Optional list of [field, direction] pairs (1=ASC, -1=DESC)
            limit (int): Optional max documents to return (default: 0 = no limit)
            skip (int): Optional number of documents to skip (default: 0)

        Returns:
            dict: Query results with data list and count
        """

        ## load args
        collection = cfgs['collection']
        query = cfgs.get('query', {})
        projection = cfgs.get('projection', None)
        sort = cfgs.get('sort', None)
        limit = int(cfgs.get('limit', 0))
        skip = int(cfgs.get('skip', 0))

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.query': query})
        self.logger.debug({'mongo.limit': limit})
        self.logger.debug({'mongo.skip': skip})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## build cursor
            col = db[collection]
            cursor = col.find(query, projection)

            ## apply sort
            if sort:
                sort_list = [(s[0], s[1]) for s in sort]
                cursor = cursor.sort(sort_list)

            ## apply skip and limit
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)

            ## collect results (convert ObjectId to str)
            data = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                data.append(doc)

            self.logger.info({'status': 'Find returned %s documents from %s' % (len(data), collection)})
            return {
                'status': True,
                'data': data,
                'count': len(data)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error finding documents: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

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

        ## load args
        collection = cfgs['collection']
        query = cfgs.get('query', {})

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.query': query})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'data': None
                }

            ## find one document
            col = db[collection]
            doc = col.find_one(query)

            ## convert ObjectId to str
            if doc:
                doc['_id'] = str(doc['_id'])

            self.logger.info({'status': 'findOne completed for collection %s' % (collection)})
            return {
                'status': True,
                'data': doc
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error finding document: %s' % (e)})
            return {
                'status': False,
                'data': None
            }

    ## def insert(self, collection, data) -> dict:
    def insert(self, context: dict, cfgs: dict) -> dict:
        """
        Insert one or more documents into a collection.

        Args:
            collection (str): Collection name
            data (dict or list): Single document dict or list of document dicts

        Returns:
            dict: Insertion result with inserted_count and inserted_ids
        """

        ## load args
        collection = cfgs['collection']
        data = cfgs['data']

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.data_type': type(data).__name__})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'inserted_count': 0,
                    'inserted_ids': []
                }

            col = db[collection]

            ## insert many or one
            if isinstance(data, list):
                result = col.insert_many(data)
                inserted_ids = [str(i) for i in result.inserted_ids]
                inserted_count = len(inserted_ids)
            else:
                result = col.insert_one(data)
                inserted_ids = [str(result.inserted_id)]
                inserted_count = 1

            self.logger.info({'status': 'Inserted %s documents into %s' % (inserted_count, collection)})
            return {
                'status': True,
                'inserted_count': inserted_count,
                'inserted_ids': inserted_ids
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error inserting documents: %s' % (e)})
            return {
                'status': False,
                'inserted_count': 0,
                'inserted_ids': []
            }

    ## def update(self, collection, query, update, multi) -> dict:
    def update(self, context: dict, cfgs: dict) -> dict:
        """
        Update documents matching a query.

        Args:
            collection (str): Collection name
            query (dict): MongoDB filter query
            update (dict): Update document (e.g. {"$set": {"field": "value"}})
            multi (bool): Update all matching documents (default: False = update one)

        Returns:
            dict: Update result with matched and modified counts
        """

        ## load args
        collection = cfgs['collection']
        query = cfgs['query']
        update_doc = cfgs['update']
        multi = cfgs.get('multi', False)

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.query': query})
        self.logger.debug({'mongo.multi': multi})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'matched': 0,
                    'modified': 0
                }

            col = db[collection]

            ## update many or one
            if multi:
                result = col.update_many(query, update_doc)
            else:
                result = col.update_one(query, update_doc)

            self.logger.info({'status': 'Updated %s documents in %s (matched: %s)' % (result.modified_count, collection, result.matched_count)})
            return {
                'status': True,
                'matched': result.matched_count,
                'modified': result.modified_count
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error updating documents: %s' % (e)})
            return {
                'status': False,
                'matched': 0,
                'modified': 0
            }

    ## def delete(self, collection, query, multi) -> dict:
    def delete(self, context: dict, cfgs: dict) -> dict:
        """
        Delete documents matching a query.

        Args:
            collection (str): Collection name
            query (dict): MongoDB filter query
            multi (bool): Delete all matching documents (default: False = delete one)

        Returns:
            dict: Deletion result with deleted count
        """

        ## load args
        collection = cfgs['collection']
        query = cfgs['query']
        multi = cfgs.get('multi', False)

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.query': query})
        self.logger.debug({'mongo.multi': multi})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'deleted': 0
                }

            col = db[collection]

            ## delete many or one
            if multi:
                result = col.delete_many(query)
            else:
                result = col.delete_one(query)

            self.logger.info({'status': 'Deleted %s documents from %s' % (result.deleted_count, collection)})
            return {
                'status': True,
                'deleted': result.deleted_count
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error deleting documents: %s' % (e)})
            return {
                'status': False,
                'deleted': 0
            }

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

        ## load args
        collection = cfgs['collection']
        query = cfgs.get('query', {})

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.query': query})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'count': 0
                }

            col = db[collection]
            total = col.count_documents(query)

            self.logger.info({'status': 'Count for %s: %s' % (collection, total)})
            return {
                'status': True,
                'count': total
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error counting documents: %s' % (e)})
            return {
                'status': False,
                'count': 0
            }

    ## def aggregate(self, collection, pipeline) -> dict:
    def aggregate(self, context: dict, cfgs: dict) -> dict:
        """
        Run an aggregation pipeline on a collection.

        Args:
            collection (str): Collection name
            pipeline (list): MongoDB aggregation pipeline stages

        Returns:
            dict: Aggregation results with data list and count
        """

        ## load args
        collection = cfgs['collection']
        pipeline = cfgs['pipeline']

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.pipeline_stages': len(pipeline)})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            col = db[collection]
            cursor = col.aggregate(pipeline)

            ## collect results
            data = []
            for doc in cursor:
                doc['_id'] = str(doc['_id']) if '_id' in doc else None
                data.append(doc)

            self.logger.info({'status': 'Aggregate returned %s documents from %s' % (len(data), collection)})
            return {
                'status': True,
                'data': data,
                'count': len(data)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error running aggregation: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

    ## def createIndex(self, collection, keys, unique, name) -> dict:
    def createIndex(self, context: dict, cfgs: dict) -> dict:
        """
        Create an index on a collection.

        Args:
            collection (str): Collection name
            keys (dict): Index key specification (e.g. {"field": 1} for ascending)
            unique (bool): Whether the index should enforce uniqueness (default: False)
            name (str): Optional index name

        Returns:
            dict: Index creation result
        """

        ## load args
        collection = cfgs['collection']
        keys = cfgs['keys']
        unique = cfgs.get('unique', False)
        name = cfgs.get('name', None)

        ## debug prt
        self.logger.debug({'mongo.collection': collection})
        self.logger.debug({'mongo.keys': keys})
        self.logger.debug({'mongo.unique': unique})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            col = db[collection]

            ## build index key list
            key_list = [(k, v) for k, v in keys.items()]

            ## build kwargs
            kwargs = {'unique': unique}
            if name:
                kwargs['name'] = name

            ## create index
            index_name = col.create_index(key_list, **kwargs)

            self.logger.info({'status': 'Index created on %s: %s' % (collection, index_name)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error creating index: %s' % (e)})
            return {
                'status': False
            }

    ## def dropCollection(self, collection) -> dict:
    def dropCollection(self, context: dict, cfgs: dict) -> dict:
        """
        Drop an entire collection.

        Args:
            collection (str): Collection name to drop

        Returns:
            dict: Operation status
        """

        ## load args
        collection = cfgs['collection']

        ## debug prt
        self.logger.debug({'mongo.collection': collection})

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False
                }

            ## drop collection
            db.drop_collection(collection)

            self.logger.info({'status': 'Collection dropped: %s' % (collection)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error dropping collection: %s' % (e)})
            return {
                'status': False
            }

    ## def listCollections() -> dict:
    def listCollections(self, context: dict, cfgs: dict) -> dict:
        """
        List all collection names in the current database.

        Returns:
            dict: List of collection names
        """

        try:
            ## check connection
            db = self._get_db(context)
            if db is None:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'collections': []
                }

            ## list collections
            collections = db.list_collection_names()

            self.logger.info({'status': 'Listed %s collections' % (len(collections))})
            return {
                'status': True,
                'collections': collections
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error listing collections: %s' % (e)})
            return {
                'status': False,
                'collections': []
            }
