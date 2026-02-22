"""
Prometheus Workflow Procedure Module

This module defines the Prometheus procedure class used by the workflow
engine for Prometheus metrics operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Create and manage Prometheus metric registries
    - Convert dict list data to Prometheus metrics (gauge, counter, histogram, summary)
    - Support both dynamic labels (from dict fields) and static labels
    - Push metrics to Prometheus Pushgateway
    - Write metrics to text file in Prometheus exposition format
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
from prometheus_client import (
    CollectorRegistry, Counter, Gauge, Histogram, Summary,
    push_to_gateway, write_to_textfile
)

class Prometheus(object):
    """
    Prometheus metrics connection and operation manager.

    Responsibilities:
        - Create and manage Prometheus metric registries
        - Convert dict list to Prometheus metrics
        - Support dynamic and static labels
        - Push metrics to Pushgateway
        - Write metrics to text file
    """

    ## context keys
    _CTX_REGISTRY = '__prom_registry__'
    _CTX_GATEWAY  = '__prom_gateway__'
    _CTX_JOB      = '__prom_job__'

    def __init__(self, logger: object) -> None:
        """
        Initialize the Prometheus manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _get_registry(self, context: dict):
        """Return the CollectorRegistry from context, or None."""
        return context.get(self._CTX_REGISTRY)

    def _get_gateway(self, context: dict):
        """Return the Pushgateway URL from context, or None."""
        return context.get(self._CTX_GATEWAY)

    def _get_job(self, context: dict):
        """Return the job name from context, or None."""
        return context.get(self._CTX_JOB)

    ## def connect(self, gateway: str, job: str) -> dict:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Create a fresh Prometheus CollectorRegistry and store Pushgateway URL.

        Args:
            gateway (str): Optional Pushgateway URL (default: "")
            job (str): Prometheus job label

        Returns:
            dict: Connection status
        """

        ## load args
        gateway = cfgs.get('gateway', None)
        job = cfgs['job']

        ## debug prt
        self.logger.debug({'prom.gateway': gateway})
        self.logger.debug({'prom.job': job})

        try:
            ## create registry
            context[self._CTX_REGISTRY] = CollectorRegistry()
            context[self._CTX_GATEWAY] = gateway
            context[self._CTX_JOB] = job

            self.logger.info({'status': 'Successfully created Prometheus registry for job %s' % (job)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error creating Prometheus registry: %s' % (e)})
            context[self._CTX_REGISTRY] = None
            context[self._CTX_GATEWAY] = None
            context[self._CTX_JOB] = None
            return {
                'status': False
            }

    ## def disconnect(self) -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Clear the Prometheus registry and gateway.

        This method is safe to call multiple times.
        """

        try:
            ## clear registry and gateway
            if self._get_registry(context):
                self.logger.info({'status': 'Prometheus registry cleared successfully'})

            context[self._CTX_REGISTRY] = None
            context[self._CTX_GATEWAY] = None
            context[self._CTX_JOB] = None

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error disconnecting from Prometheus: %s' % (e)})

        return {
            'status': True
        }

    ## def dicts2prom(self, data: list, metric_name: str, metric_desc: str, metric_type: str, value_col: str, label_cols: list, static_labels: dict, buckets: list) -> dict:
    def dicts2prom(self, context: dict, cfgs: dict) -> dict:
        """
        Convert a list of dicts to Prometheus metrics.

        Supports gauge, counter, histogram, and summary metric types.
        Labels can be dynamic (from dict fields) and/or static (fixed values).

        Args:
            data (ref): List of dicts from upstream workflow step
            metric_name (str): Prometheus metric name
            metric_desc (str): Optional Prometheus metric description (default: "")
            metric_type (str): Optional metric type gauge, counter, histogram, summary (default: "gauge")
            value_col (str): Field name in each dict to use as the metric value
            label_cols (list): Optional field names to use as dynamic labels (default: [])
            static_labels (dict): Optional dict of fixed labels applied to all rows (default: {})

        Returns:
            dict: Conversion result with metrics count
        """

        ## load args
        data = cfgs['data']
        metric_name = cfgs['metric_name']
        metric_desc = cfgs['metric_desc']
        metric_type = cfgs['metric_type']
        value_col = cfgs['value_col']
        label_cols = cfgs.get('label_cols', [])
        static_labels = cfgs.get('static_labels', {})
        buckets = cfgs.get('buckets', None)

        ## debug prt
        self.logger.debug({'prom.metric_name': metric_name})
        self.logger.debug({'prom.metric_desc': metric_desc})
        self.logger.debug({'prom.metric_type': metric_type})
        self.logger.debug({'prom.value_col': value_col})
        self.logger.debug({'prom.label_cols': label_cols})
        self.logger.debug({'prom.static_labels': static_labels})
        self.logger.debug({'prom.data_count': len(data)})

        try:
            ## check connection
            registry = self._get_registry(context)
            if not registry:
                self.logger.error({'status': 'Error: No active registry. Please connect first.'})
                return {
                    'status': False
                }

            ## check if data is empty
            if not data:
                self.logger.error({'status': 'Error: Data list is empty.'})
                return {
                    'status': False
                }

            ## validate metric type
            valid_types = ['gauge', 'counter', 'histogram', 'summary']
            if metric_type not in valid_types:
                self.logger.error({'status': 'Error: Invalid metric_type %s. Must be one of: %s' % (metric_type, valid_types)})
                return {
                    'status': False
                }

            ## build label names from dynamic label_cols and static_labels keys
            all_label_names = list(label_cols) + list(static_labels.keys())

            ## create metric based on metric_type
            metric_classes = {
                'gauge': Gauge,
                'counter': Counter,
                'histogram': Histogram,
                'summary': Summary
            }
            metric_cls = metric_classes[metric_type]

            ## build metric kwargs
            metric_kwargs = {
                'name': metric_name,
                'documentation': metric_desc,
                'labelnames': all_label_names,
                'registry': registry
            }

            ## set histogram buckets
            if metric_type == 'histogram' and buckets:
                metric_kwargs['buckets'] = buckets

            ## create metric instance
            metric = metric_cls(**metric_kwargs)

            ## process data - iterate dict list and set metric values
            metrics_count = 0
            for row in data:
                ## extract dynamic label values from dict
                label_values = {}
                for col in label_cols:
                    label_values[col] = str(row[col])

                ## merge with static labels
                label_values.update(static_labels)

                ## extract metric value
                value = float(row[value_col])

                ## set metric value based on type
                if metric_type == 'gauge':
                    metric.labels(**label_values).set(value)

                elif metric_type == 'counter':
                    metric.labels(**label_values).inc(value)

                elif metric_type == 'histogram':
                    metric.labels(**label_values).observe(value)

                elif metric_type == 'summary':
                    metric.labels(**label_values).observe(value)

                metrics_count += 1

            self.logger.info({'status': 'Successfully converted %s rows to %s metric %s' % (metrics_count, metric_type, metric_name)})
            return {
                'status': True,
                'metrics_count': metrics_count
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error converting dicts to Prometheus metrics: %s' % (e)})
            return {
                'status': False
            }

    ## def push(self) -> dict:
    def push(self, context: dict, cfgs: dict) -> dict:
        """
        Push all registered metrics to Prometheus Pushgateway.

        Returns:
            dict: Push result
        """

        try:
            ## check connection
            registry = self._get_registry(context)
            if not registry:
                self.logger.error({'status': 'Error: No active registry. Please connect first.'})
                return {
                    'status': False
                }

            ## check gateway
            gateway = self._get_gateway(context)
            if not gateway:
                self.logger.error({'status': 'Error: No Pushgateway URL configured. Please set gateway in connect.'})
                return {
                    'status': False
                }

            ## check job
            job = self._get_job(context)
            if not job:
                self.logger.error({'status': 'Error: No job name configured. Please set job in connect.'})
                return {
                    'status': False
                }

            ## push to gateway
            push_to_gateway(gateway, job=job, registry=registry)

            self.logger.info({'status': 'Successfully pushed metrics to Pushgateway at %s for job %s' % (gateway, job)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error pushing metrics to Pushgateway: %s' % (e)})
            return {
                'status': False
            }

    ## def write(self, file_path: str) -> dict:
    def write(self, context: dict, cfgs: dict) -> dict:
        """
        Write all registered metrics to a text file in Prometheus exposition format.

        Args:
            file_path (str): Output file path for the .prom file

        Returns:
            dict: Write result
        """

        ## load args
        file_path = cfgs['file_path']

        ## debug prt
        self.logger.debug({'prom.file_path': file_path})

        try:
            ## check connection
            registry = self._get_registry(context)
            if not registry:
                self.logger.error({'status': 'Error: No active registry. Please connect first.'})
                return {
                    'status': False
                }

            ## write to text file
            write_to_textfile(file_path, registry)

            self.logger.info({'status': 'Successfully wrote metrics to file %s' % (file_path)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error writing metrics to file: %s' % (e)})
            return {
                'status': False
            }
