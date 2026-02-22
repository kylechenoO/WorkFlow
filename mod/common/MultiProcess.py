"""
MultiProcess Workflow Procedure Module

This module defines the MultiProcess procedure class used by the workflow
engine for parallel execution operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Execute multiple workflow steps in parallel using multiprocessing
    - Split large data sets and process chunks in parallel
    - Collect and merge results from parallel workers
    - Handle worker failures with structured error reporting
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import sys
import importlib
import logging
from multiprocessing import Pool


def _create_worker_logger(name='MultiProcess.worker'):
    """
    Create a minimal console logger for use in worker processes.

    Worker processes cannot inherit the main logger because logging
    handlers (file handles, MySQL connections) are not picklable.

    Args:
        name (str): Logger name

    Returns:
        logging.Logger: A basic console logger
    """

    logger = logging.getLogger(name)
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger.setLevel(logging.DEBUG)
    return logger


def _worker_step(step_cfg):
    """
    Top-level worker function for parallel_steps.

    Executes a single workflow step in a worker process. This function
    must be defined at module level to be picklable by multiprocessing.

    Args:
        step_cfg (dict): Step configuration with keys:
            - name (str): Step name
            - mod (str): Module path
            - method (str): Method name
            - params (dict): Method parameters
            - _mod_paths (list): sys.path entries to inject

    Returns:
        dict: Execution result with name, status, and result or error
    """

    name = step_cfg.get('name', 'unknown')
    try:
        ## ensure module search paths are available in worker
        mod_paths = step_cfg.get('_mod_paths', [])
        for p in mod_paths:
            if p not in sys.path:
                sys.path.insert(0, p)

        ## create worker logger
        logger = _create_worker_logger('MultiProcess.worker.%s' % (name))

        ## load module and class (same pattern as Flow.execFlow)
        mod = step_cfg['mod']
        method = step_cfg['method']
        params = step_cfg.get('params', {})

        module = importlib.import_module(mod)
        cls_name = mod.split('.')[-1]
        cls = getattr(module, cls_name)
        inst = cls(logger)
        func = getattr(inst, method)

        ## execute with empty context
        context = {}
        result = func(context, params)

        return {
            'name': name,
            'status': True,
            'result': result
        }

    except Exception as e:
        logger = _create_worker_logger('MultiProcess.worker.%s' % (name))
        logger.error({'status': 'Error in worker step %s: %s' % (name, e)})
        return {
            'name': name,
            'status': False,
            'error': str(e)
        }


def _worker_data(worker_cfg):
    """
    Top-level worker function for parallel_data.

    Processes a single chunk of data in a worker process. This function
    must be defined at module level to be picklable by multiprocessing.

    Args:
        worker_cfg (dict): Worker configuration with keys:
            - mod (str): Module path
            - method (str): Method name
            - params (dict): Method parameters
            - chunk (list): Data chunk to process
            - data_key (str): Key name in params for chunk data
            - chunk_index (int): Index of this chunk for logging
            - _mod_paths (list): sys.path entries to inject

    Returns:
        dict: Processing result with status and data list
    """

    chunk_index = worker_cfg.get('chunk_index', 0)
    try:
        ## ensure module search paths are available in worker
        mod_paths = worker_cfg.get('_mod_paths', [])
        for p in mod_paths:
            if p not in sys.path:
                sys.path.insert(0, p)

        ## create worker logger
        logger = _create_worker_logger('MultiProcess.worker.chunk_%s' % (chunk_index))

        ## load module and class
        mod = worker_cfg['mod']
        method = worker_cfg['method']
        params = dict(worker_cfg.get('params', {}))
        chunk = worker_cfg['chunk']
        data_key = worker_cfg['data_key']

        ## replace data_key in params with this chunk
        params[data_key] = chunk

        ## dynamic import
        module = importlib.import_module(mod)
        cls_name = mod.split('.')[-1]
        cls = getattr(module, cls_name)
        inst = cls(logger)
        func = getattr(inst, method)

        ## execute with empty context
        context = {}
        result = func(context, params)

        ## extract data from result
        data = result.get('data', [])

        return {
            'status': True,
            'chunk_index': chunk_index,
            'data': data
        }

    except Exception as e:
        logger = _create_worker_logger('MultiProcess.worker.chunk_%s' % (chunk_index))
        logger.error({'status': 'Error in worker chunk %s: %s' % (chunk_index, e)})
        return {
            'status': False,
            'chunk_index': chunk_index,
            'error': str(e),
            'data': []
        }


class MultiProcess(object):
    """
    Parallel execution manager for workflow procedures.

    Responsibilities:
        - Execute multiple workflow steps concurrently
        - Split and process data in parallel chunks
        - Collect and merge results from workers
        - Handle worker failures with structured error reporting
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the MultiProcess manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    ## def parallel_steps(self, steps: list, processes: int) -> dict:
    def parallel_steps(self, context: dict, cfgs: dict) -> dict:
        """
        Execute multiple workflow steps in parallel.

        Each step runs in its own process with a fresh module instance.
        Workers do not share context. Results are collected and returned
        as a dict keyed by step name.

        Args:
            steps (list): List of step config dicts (default: [])
            processes (int): Optional number of worker processes (default: 4)

        Returns:
            dict: Parallel execution results
        """

        ## load args
        steps = cfgs['steps']
        processes = int(cfgs.get('processes', len(steps)))

        ## debug prt
        self.logger.debug({'mp.steps_count': len(steps)})
        self.logger.debug({'mp.processes': processes})

        try:
            ## validate steps
            if not steps:
                self.logger.error({'status': 'Error: steps list is empty'})
                return {
                    'status': False,
                    'results': {},
                    'errors': []
                }

            ## inject sys.path into each step config for worker processes
            mod_paths = list(sys.path)
            for step in steps:
                step['_mod_paths'] = mod_paths

            ## execute steps in parallel
            self.logger.info({'status': 'Starting parallel execution of %s steps with %s processes' % (len(steps), processes)})

            pool = Pool(processes=processes)
            worker_results = pool.map(_worker_step, steps)
            pool.close()
            pool.join()

            ## collect results
            results = {}
            errors = []
            for wr in worker_results:
                step_name = wr['name']
                if wr['status']:
                    results[step_name] = wr['result']
                else:
                    results[step_name] = {
                        'status': False,
                        'error': wr.get('error', 'Unknown error')
                    }
                    errors.append(step_name)

            self.logger.info({'status': 'Parallel execution completed: %s succeeded, %s failed' % (len(steps) - len(errors), len(errors))})
            return {
                'status': len(errors) == 0,
                'results': results,
                'errors': errors
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error in parallel_steps: %s' % (e)})
            return {
                'status': False,
                'results': {},
                'errors': [str(e)]
            }

    ## def parallel_data(self, data: list, data_key: str, mod: str, method: str, params: dict, processes: int) -> dict:
    def parallel_data(self, context: dict, cfgs: dict) -> dict:
        """
        Split data into chunks and process each chunk in parallel.

        Each chunk is processed in its own process with a fresh module instance.
        Results are merged back into a single flat list of dicts.

        Args:
            data (ref): List of dicts to split across workers
            data_key (str): Optional key name in params where each chunk is placed (default: "data")
            mod (str): Target module path
            method (str): Target method name
            params (dict): Optional additional params for target method (default: {})
            processes (int): Optional number of workers (default: 4)

        Returns:
            dict: Merged processing results
        """

        ## load args
        data = cfgs['data']
        data_key = cfgs['data_key']
        mod = cfgs['mod']
        method = cfgs['method']
        params = cfgs.get('params', {})
        processes = int(cfgs.get('processes', 4))

        ## debug prt
        self.logger.debug({'mp.data_count': len(data)})
        self.logger.debug({'mp.data_key': data_key})
        self.logger.debug({'mp.mod': mod})
        self.logger.debug({'mp.method': method})
        self.logger.debug({'mp.processes': processes})

        try:
            ## validate data
            if not data:
                self.logger.error({'status': 'Error: data list is empty'})
                return {
                    'status': False,
                    'data': [],
                    'errors': []
                }

            ## split data into chunks
            chunk_size = max(1, len(data) // processes)
            chunks = []
            for i in range(0, len(data), chunk_size):
                chunks.append(data[i:i + chunk_size])

            self.logger.info({'status': 'Splitting %s records into %s chunks' % (len(data), len(chunks))})

            ## inject sys.path and build worker configs
            mod_paths = list(sys.path)
            worker_cfgs = []
            for idx, chunk in enumerate(chunks):
                worker_cfg = {
                    'mod': mod,
                    'method': method,
                    'params': params,
                    'chunk': chunk,
                    'data_key': data_key,
                    'chunk_index': idx,
                    '_mod_paths': mod_paths
                }
                worker_cfgs.append(worker_cfg)

            ## execute chunks in parallel
            pool = Pool(processes=min(processes, len(chunks)))
            worker_results = pool.map(_worker_data, worker_cfgs)
            pool.close()
            pool.join()

            ## merge results (pool.map preserves order)
            merged_data = []
            errors = []
            for wr in worker_results:
                if wr['status']:
                    merged_data.extend(wr['data'])
                else:
                    errors.append('chunk_%s: %s' % (wr['chunk_index'], wr.get('error', 'Unknown error')))

            if errors:
                self.logger.error({'status': 'Error in parallel_data: %s chunks failed' % (len(errors))})

            self.logger.info({'status': 'Parallel data processing completed: %s records merged' % (len(merged_data))})
            return {
                'status': len(errors) == 0,
                'data': merged_data,
                'errors': errors
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error in parallel_data: %s' % (e)})
            return {
                'status': False,
                'data': [],
                'errors': [str(e)]
            }
