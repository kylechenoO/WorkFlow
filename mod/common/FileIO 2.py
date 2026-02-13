"""
FileIO Workflow Procedure Module

This module defines the FileIO procedure class used by the workflow
engine for file read and write operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Read data from CSV, JSON, Excel, YAML files
    - Write data to CSV, JSON, Excel, YAML files
    - Auto-detect file format from extension
    - Return data as list of dicts for workflow context
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import os
import csv
import json
import yaml
import pandas as pd

class FileIO(object):
    """
    File read/write manager for workflow procedures.

    Responsibilities:
        - Read files (CSV, JSON, Excel, YAML) into list of dicts
        - Write list of dicts to files
        - Auto-detect format from file extension
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the FileIO manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _detect_format(self, file_path: str, explicit_format: str) -> str:
        """
        Detect file format from extension or explicit format parameter.

        Args:
            file_path (str): File path
            explicit_format (str): Explicit format override or None

        Returns:
            str: Detected format (csv, json, xlsx, yaml)
        """

        if explicit_format:
            return explicit_format

        ## extract extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        ## map extension to format
        ext_map = {
            '.csv': 'csv',
            '.json': 'json',
            '.xlsx': 'xlsx',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }

        if ext in ext_map:
            return ext_map[ext]

        raise ValueError('Unsupported file extension: %s' % (ext))

    ## def read(self, file_path: str, format: str, encoding: str, sheet: str) -> dict:
    def read(self, context: dict, cfgs: dict) -> dict:
        """
        Read a file and return data as a list of dicts.

        Args:
            file_path (str): Path to input file
            format (str): Optional file format (csv, json, xlsx, yaml)
            encoding (str): Optional file encoding, default utf-8
            sheet (str): Optional Excel sheet name

        Returns:
            dict: Read result with data list
        """

        ## load args
        file_path = cfgs['file_path']
        fmt = cfgs.get('format', None)
        encoding = cfgs.get('encoding', 'utf-8')
        sheet = cfgs.get('sheet', None)

        ## debug prt
        self.logger.debug({'fileio.file_path': file_path})
        self.logger.debug({'fileio.format': fmt})
        self.logger.debug({'fileio.encoding': encoding})

        try:
            ## detect format
            fmt = self._detect_format(file_path, fmt)
            self.logger.debug({'fileio.detected_format': fmt})

            ## read CSV
            if fmt == 'csv':
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    data = list(reader)

            ## read JSON
            elif fmt == 'json':
                with open(file_path, 'r', encoding=encoding) as f:
                    data = json.load(f)
                ## wrap single dict in list
                if isinstance(data, dict):
                    data = [data]

            ## read Excel
            elif fmt == 'xlsx':
                sheet_name = sheet if sheet else 0
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
                data = df.to_dict(orient='records')

            ## read YAML
            elif fmt == 'yaml':
                with open(file_path, 'r', encoding=encoding) as f:
                    data = yaml.safe_load(f)
                ## wrap single dict in list
                if isinstance(data, dict):
                    data = [data]

            else:
                self.logger.error({'status': 'Error: unsupported format %s' % (fmt)})
                return {
                    'status': False,
                    'data': []
                }

            self.logger.info({'status': 'Successfully read %s rows from %s' % (len(data), file_path)})
            return {
                'status': True,
                'data': data
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error reading file %s: %s' % (file_path, e)})
            return {
                'status': False,
                'data': []
            }

    ## def write(self, file_path: str, data: list, format: str, encoding: str, sheet: str) -> dict:
    def write(self, context: dict, cfgs: dict) -> dict:
        """
        Write a list of dicts to a file.

        Args:
            file_path (str): Path to output file
            data (list): List of dicts to write
            format (str): Optional file format (csv, json, xlsx, yaml)
            encoding (str): Optional file encoding, default utf-8
            sheet (str): Optional Excel sheet name, default Sheet1

        Returns:
            dict: Write result
        """

        ## load args
        file_path = cfgs['file_path']
        data = cfgs['data']
        fmt = cfgs.get('format', None)
        encoding = cfgs.get('encoding', 'utf-8')
        sheet = cfgs.get('sheet', 'Sheet1')

        ## debug prt
        self.logger.debug({'fileio.file_path': file_path})
        self.logger.debug({'fileio.format': fmt})
        self.logger.debug({'fileio.data_count': len(data)})

        try:
            ## detect format
            fmt = self._detect_format(file_path, fmt)
            self.logger.debug({'fileio.detected_format': fmt})

            ## write CSV
            if fmt == 'csv':
                if not data:
                    self.logger.error({'status': 'Error: data list is empty, cannot write CSV'})
                    return {
                        'status': False
                    }
                fieldnames = list(data[0].keys())
                with open(file_path, 'w', encoding=encoding, newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)

            ## write JSON
            elif fmt == 'json':
                with open(file_path, 'w', encoding=encoding) as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            ## write Excel
            elif fmt == 'xlsx':
                df = pd.DataFrame(data)
                df.to_excel(file_path, sheet_name=sheet, index=False, engine='openpyxl')

            ## write YAML
            elif fmt == 'yaml':
                with open(file_path, 'w', encoding=encoding) as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            else:
                self.logger.error({'status': 'Error: unsupported format %s' % (fmt)})
                return {
                    'status': False
                }

            self.logger.info({'status': 'Successfully wrote %s rows to %s' % (len(data), file_path)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error writing file %s: %s' % (file_path, e)})
            return {
                'status': False
            }
