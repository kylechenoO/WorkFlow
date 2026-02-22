"""
Kafka Workflow Procedure Module

This module defines the Kafka procedure class used by the workflow
engine for Apache Kafka producer and consumer operations. The class
methods are invoked dynamically by the Flow engine during workflow execution.

The Kafka producer and consumer are stored in the workflow context under
reserved keys so they persist across multiple procedure steps that share
the same context.

Responsibilities:
    - Connect as a Kafka producer or consumer
    - Send JSON-serialized messages to topics
    - Consume messages from subscribed topics
    - Support PLAINTEXT, SSL, SASL_PLAINTEXT, and SASL_SSL security protocols
    - List available topics
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError


class Kafka(object):
    """
    Kafka producer and consumer manager.

    The producer and consumer objects are stored in the workflow context
    (not in self) so they persist across procedure steps within the same
    workflow run.

    Responsibilities:
        - Connect as producer or consumer with optional SASL/SSL auth
        - Send JSON-serialized messages
        - Consume and deserialize messages
        - List available topics
    """

    ## context keys for connection objects
    _CTX_PRODUCER = '__kafka_producer__'
    _CTX_CONSUMER = '__kafka_consumer__'

    def __init__(self, logger: object) -> None:
        """
        Initialize the Kafka manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _get_producer(self, context: dict):
        """Return the KafkaProducer stored in context, or None."""
        return context.get(self._CTX_PRODUCER)

    def _get_consumer(self, context: dict):
        """Return the KafkaConsumer stored in context, or None."""
        return context.get(self._CTX_CONSUMER)

    def _build_security_kwargs(self, cfgs: dict) -> dict:
        """
        Build security-related kwargs from cfgs for KafkaProducer/KafkaConsumer.

        Args:
            cfgs (dict): Configuration dict with optional security fields

        Returns:
            dict: Security kwargs to merge into client kwargs
        """

        kwargs = {}

        security_protocol = cfgs.get('security_protocol', 'PLAINTEXT')
        kwargs['security_protocol'] = security_protocol

        ## sasl settings
        if security_protocol in ('SASL_PLAINTEXT', 'SASL_SSL'):
            sasl_mechanism = cfgs.get('sasl_mechanism', 'PLAIN')
            sasl_username = cfgs.get('sasl_username', None)
            sasl_password = cfgs.get('sasl_password', None)
            kwargs['sasl_mechanism'] = sasl_mechanism

            if sasl_username and sasl_password:
                kwargs['sasl_plain_username'] = sasl_username
                kwargs['sasl_plain_password'] = sasl_password

        ## ssl settings
        if security_protocol in ('SSL', 'SASL_SSL'):
            ssl_cafile = cfgs.get('ssl_cafile', None)
            ssl_certfile = cfgs.get('ssl_certfile', None)
            ssl_keyfile = cfgs.get('ssl_keyfile', None)

            if ssl_cafile:
                kwargs['ssl_cafile'] = ssl_cafile
            if ssl_certfile:
                kwargs['ssl_certfile'] = ssl_certfile
            if ssl_keyfile:
                kwargs['ssl_keyfile'] = ssl_keyfile

        return kwargs

    ## def connect_producer(self, bootstrap_servers, client_id, acks, retries, ...) -> dict:
    def connect_producer(self, context: dict, cfgs: dict) -> dict:
        """
        Connect as a Kafka producer.

        Args:
            bootstrap_servers (str or list): Kafka broker addresses (default: "localhost:9092")
            client_id (str): Optional client identifier
            acks (str or int): Acknowledgement policy: "all", 0, 1 (default: "all")
            retries (int): Number of retries on send failure (default: 3)
            security_protocol (str): PLAINTEXT / SSL / SASL_PLAINTEXT / SASL_SSL (default: "PLAINTEXT")
            sasl_mechanism (str): PLAIN / SCRAM-SHA-256 / SCRAM-SHA-512 (default: "PLAIN")
            sasl_username (str): SASL username (never logged)
            sasl_password (str): SASL password (never logged)
            ssl_cafile (str): CA certificate file path
            ssl_certfile (str): Client certificate file path
            ssl_keyfile (str): Client private key file path (never logged)

        Returns:
            dict: Connection status
        """

        ## load args
        bootstrap_servers = cfgs.get('bootstrap_servers', 'localhost:9092')
        client_id = cfgs.get('client_id', 'workflow-producer')
        acks = cfgs.get('acks', 'all')
        retries = int(cfgs.get('retries', 3))

        ## debug prt (never log sasl_password or ssl_keyfile)
        self.logger.debug({'kafka.bootstrap_servers': bootstrap_servers})
        self.logger.debug({'kafka.client_id': client_id})
        self.logger.debug({'kafka.acks': acks})
        self.logger.debug({'kafka.retries': retries})
        self.logger.debug({'kafka.security_protocol': cfgs.get('security_protocol', 'PLAINTEXT')})

        try:
            ## build producer kwargs
            kwargs = {
                'bootstrap_servers': bootstrap_servers,
                'client_id': client_id,
                'acks': acks,
                'retries': retries,
                'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
                'key_serializer': lambda k: k.encode('utf-8') if k else None
            }

            ## merge security kwargs
            kwargs.update(self._build_security_kwargs(cfgs))

            ## connect producer and store in context
            context[self._CTX_PRODUCER] = KafkaProducer(**kwargs)

            self.logger.info({'status': 'Kafka producer connected to %s' % (bootstrap_servers)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting Kafka producer: %s' % (e)})
            context[self._CTX_PRODUCER] = None
            return {
                'status': False
            }

    ## def connect_consumer(self, bootstrap_servers, group_id, topics, ...) -> dict:
    def connect_consumer(self, context: dict, cfgs: dict) -> dict:
        """
        Connect as a Kafka consumer and subscribe to topics.

        Args:
            bootstrap_servers (str or list): Kafka broker addresses (default: "localhost:9092")
            group_id (str): Consumer group ID
            topics (list): List of topic names to subscribe to
            auto_offset_reset (str): "earliest" or "latest" (default: "latest")
            enable_auto_commit (bool): Auto-commit offsets (default: True)
            security_protocol (str): PLAINTEXT / SSL / SASL_PLAINTEXT / SASL_SSL (default: "PLAINTEXT")
            sasl_mechanism (str): PLAIN / SCRAM-SHA-256 / SCRAM-SHA-512 (default: "PLAIN")
            sasl_username (str): SASL username (never logged)
            sasl_password (str): SASL password (never logged)
            ssl_cafile (str): CA certificate file path
            ssl_certfile (str): Client certificate file path
            ssl_keyfile (str): Client private key file path (never logged)

        Returns:
            dict: Connection status
        """

        ## load args
        bootstrap_servers = cfgs.get('bootstrap_servers', 'localhost:9092')
        group_id = cfgs.get('group_id', 'workflow-consumer')
        topics = cfgs['topics']
        auto_offset_reset = cfgs.get('auto_offset_reset', 'latest')
        enable_auto_commit = cfgs.get('enable_auto_commit', True)

        ## debug prt (never log sasl_password or ssl_keyfile)
        self.logger.debug({'kafka.bootstrap_servers': bootstrap_servers})
        self.logger.debug({'kafka.group_id': group_id})
        self.logger.debug({'kafka.topics': topics})
        self.logger.debug({'kafka.auto_offset_reset': auto_offset_reset})
        self.logger.debug({'kafka.enable_auto_commit': enable_auto_commit})
        self.logger.debug({'kafka.security_protocol': cfgs.get('security_protocol', 'PLAINTEXT')})

        try:
            ## build consumer kwargs
            kwargs = {
                'bootstrap_servers': bootstrap_servers,
                'group_id': group_id,
                'auto_offset_reset': auto_offset_reset,
                'enable_auto_commit': enable_auto_commit,
                'value_deserializer': lambda v: json.loads(v.decode('utf-8')) if v else None,
                'consumer_timeout_ms': 1000
            }

            ## merge security kwargs
            kwargs.update(self._build_security_kwargs(cfgs))

            ## connect consumer and subscribe, store in context
            context[self._CTX_CONSUMER] = KafkaConsumer(*topics, **kwargs)

            self.logger.info({'status': 'Kafka consumer connected to %s, subscribed to %s' % (bootstrap_servers, topics)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting Kafka consumer: %s' % (e)})
            context[self._CTX_CONSUMER] = None
            return {
                'status': False
            }

    ## def disconnect() -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close any active Kafka producer and consumer connections.

        This method is safe to call multiple times.
        """

        try:
            ## close producer
            producer = self._get_producer(context)
            if producer:
                producer.flush()
                producer.close()
                self.logger.info({'status': 'Kafka producer closed'})
            context[self._CTX_PRODUCER] = None

            ## close consumer
            consumer = self._get_consumer(context)
            if consumer:
                consumer.close()
                self.logger.info({'status': 'Kafka consumer closed'})
            context[self._CTX_CONSUMER] = None

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error disconnecting Kafka: %s' % (e)})

        return {
            'status': True
        }

    ## def send(self, topic, value, key, partition) -> dict:
    def send(self, context: dict, cfgs: dict) -> dict:
        """
        Send a message to a Kafka topic.

        The value is automatically JSON-serialized before sending.

        Args:
            topic (str): Target topic name
            value (dict or str): Message value to send
            key (str): Optional message key
            partition (int): Optional target partition

        Returns:
            dict: Send result with topic, partition, and offset
        """

        ## load args
        topic = cfgs['topic']
        value = cfgs['value']
        key = cfgs.get('key', None)
        partition = cfgs.get('partition', None)

        ## debug prt
        self.logger.debug({'kafka.topic': topic})
        self.logger.debug({'kafka.key': key})
        self.logger.debug({'kafka.partition': partition})

        try:
            ## check connection
            producer = self._get_producer(context)
            if not producer:
                self.logger.error({'status': 'Error: No active producer. Please connect_producer first.'})
                return {
                    'status': False
                }

            ## build send kwargs
            kwargs = {
                'topic': topic,
                'value': value
            }

            if key:
                kwargs['key'] = key

            if partition is not None:
                kwargs['partition'] = int(partition)

            ## send message and get metadata
            future = producer.send(**kwargs)
            producer.flush()
            metadata = future.get(timeout=10)

            self.logger.info({'status': 'Message sent to %s partition %s offset %s' % (metadata.topic, metadata.partition, metadata.offset)})
            return {
                'status': True,
                'topic': metadata.topic,
                'partition': metadata.partition,
                'offset': metadata.offset
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error sending Kafka message: %s' % (e)})
            return {
                'status': False
            }

    ## def consume(self, timeout_ms, max_records, auto_commit) -> dict:
    def consume(self, context: dict, cfgs: dict) -> dict:
        """
        Poll and consume messages from subscribed topics.

        Args:
            timeout_ms (int): Poll timeout in milliseconds (default: 5000)
            max_records (int): Max number of records to return (default: 100)
            auto_commit (bool): Commit offsets after consuming (default: True)

        Returns:
            dict: Consumed messages as a list of dicts with topic, partition, offset, key, value
        """

        ## load args
        timeout_ms = int(cfgs.get('timeout_ms', 5000))
        max_records = int(cfgs.get('max_records', 100))
        auto_commit = cfgs.get('auto_commit', True)

        ## debug prt
        self.logger.debug({'kafka.timeout_ms': timeout_ms})
        self.logger.debug({'kafka.max_records': max_records})

        try:
            ## check connection
            consumer = self._get_consumer(context)
            if not consumer:
                self.logger.error({'status': 'Error: No active consumer. Please connect_consumer first.'})
                return {
                    'status': False,
                    'data': [],
                    'count': 0
                }

            ## poll for records
            records = consumer.poll(timeout_ms=timeout_ms, max_records=max_records)

            ## flatten partition records into list
            data = []
            for tp, messages in records.items():
                for msg in messages:
                    data.append({
                        'topic': msg.topic,
                        'partition': msg.partition,
                        'offset': msg.offset,
                        'key': msg.key.decode('utf-8') if msg.key else None,
                        'value': msg.value
                    })

            ## commit offsets if enabled
            if auto_commit and data:
                consumer.commit()

            self.logger.info({'status': 'Consumed %s messages' % (len(data))})
            return {
                'status': True,
                'data': data,
                'count': len(data)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error consuming Kafka messages: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'count': 0
            }

    ## def commit() -> dict:
    def commit(self, context: dict, cfgs: dict) -> dict:
        """
        Manually commit consumer offsets.

        Returns:
            dict: Commit status
        """

        try:
            ## check connection
            consumer = self._get_consumer(context)
            if not consumer:
                self.logger.error({'status': 'Error: No active consumer. Please connect_consumer first.'})
                return {
                    'status': False
                }

            ## commit offsets
            consumer.commit()

            self.logger.info({'status': 'Kafka consumer offsets committed'})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error committing Kafka offsets: %s' % (e)})
            return {
                'status': False
            }

    ## def list_topics() -> dict:
    def list_topics(self, context: dict, cfgs: dict) -> dict:
        """
        List available topics on the Kafka cluster.

        Returns:
            dict: List of topic names
        """

        try:
            ## check connection
            consumer = self._get_consumer(context)
            producer = self._get_producer(context)

            if not consumer and not producer:
                self.logger.error({'status': 'Error: No active connection. Please connect first.'})
                return {
                    'status': False,
                    'topics': []
                }

            ## get topics from consumer (preferred) or producer
            if consumer:
                topics = list(consumer.topics())
            else:
                topics = [t for t in producer._metadata.topics.keys()]

            self.logger.info({'status': 'Listed %s topics' % (len(topics))})
            return {
                'status': True,
                'topics': sorted(topics)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error listing Kafka topics: %s' % (e)})
            return {
                'status': False,
                'topics': []
            }
