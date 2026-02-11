"""
Configuration Loader Module

This module provides a Config class responsible for loading and
normalizing application configuration from a JSON5 configuration file.
It also ensures required directories exist at runtime.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

# import buildin pkgs
import os
import sys
import json5

class Config(object):
    """
    Application configuration manager.

    This class loads the global configuration file, resolves relative
    paths into absolute paths based on the project root, normalizes
    configuration values, and initializes required directories.
    """

    def __init__(self, workpath: str) -> None:
        """
        Initialize the configuration manager.

        Args:
            workpath (str): Absolute path to the project root directory
        """

        ## get workpath
        self.workpath = workpath

        ## set config file point
        global_fp = '%s/etc/global.json' % (self.workpath)

        ## load global.json
        with open(global_fp, "r") as fp:
            self.config = json5.load(fp)

        ## log config
        self.config['log']['path'] = self.config['log']['path'] if self.config['log']['path'].startswith('/') else '%s/%s' % (self.workpath, self.config['log']['path']) 
        self.config['log']['file'] = '%s/%s' % (self.config['log']['path'], self.config['log']['file'])
        self.config['log']['level'] = self.config['log']['level'].upper()
        self.config['log']['rotate']['max_size'] = int(self.config['log']['rotate']['max_size'])
        self.config['log']['rotate']['backup_count'] = int(self.config['log']['rotate']['backup_count'])

        ## lib config
        self.config['lib']['path'] = self.config['lib']['path'] if self.config['lib']['path'].startswith('/') else '%s/%s' % (self.workpath, self.config['lib']['path']) 

        ## mod config
        self.config['mod']['path'] = self.config['mod']['path'] if self.config['mod']['path'].startswith('/') else '%s/%s' % (self.workpath, self.config['mod']['path']) 

        ## init folders
        paths = [ v['path'] for k, v  in self.config.items() if 'path' in v ]
        for path in paths:
            self.dirInit(path)

        return None

    def dirInit(self, fn: str) -> bool:
        """
        Ensure a directory exists.

        This method creates the directory if it does not already exist.

        Args:
            fn (str): Directory path to initialize

        Returns:
            bool: True if the directory exists or was created successfully
        """

        if not os.path.exists(fn):
            try:
                os.mkdir(fn)

            except Exception as e:
                sys.stderr.write('[Error][%s]' % (e))
                sys.stderr.flush()

        return True
