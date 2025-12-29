"""
Logging Infrastructure Module

This module provides a structured logging system for the workflow engine.
It supports:
    - JSON-formatted logs
    - Console and rotating file output
    - Optional MySQL-backed log persistence

The design ensures that logging failures never interrupt the main workflow.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import build in pkgs
import os
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

class _MySQLLogHandler(logging.Handler):
    """
    Internal MySQL logging handler.

    This handler writes log records into a MySQL table. It is designed
    to be fail-safe: logging errors must never propagate to the main
    application logic.
    """

    def __init__(self, mysql_obj: object, table: str) -> None:
        """
        Initialize the MySQL log handler.

        Args:
            mysql_obj (object): Active MySQL connection wrapper
        """

        super().__init__()
        self.mysql = mysql_obj
        self.table = table

    def emit(self, record: str) -> None:
        """
        Emit a log record to the MySQL database.

        Any exception raised during logging is silently handled to
        prevent disruption of the main execution flow.

        Args:
            record (logging.LogRecord): Log record to persist
        """

        try:
            msg = self.format(record)

            sql = f"""
                INSERT INTO `{self.table}`
                (`level`, `logger_name`, `message`)
                VALUES (%s, %s, %s)
            """
            params = (
                record.levelname,
                record.name,
                msg,
            )

            self.mysql.cur.execute(sql, params)
            self.mysql.con.commit()

        except Exception:
            # Logging must never break main workflow
            try:
                if getattr(self.mysql, "con", None):
                    self.mysql.con.rollback()
            except Exception:
                pass

class _JsonFormatter(logging.Formatter):
    """
    Internal JSON log formatter.

    Converts log records into structured JSON objects and ensures that
    all message content is JSON-serializable.
    """

    ## set timestmap format
    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s.%03d"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        Args:
            record (logging.LogRecord): Log record to format

        Returns:
            str: JSON-formatted log entry
        """

        log_record = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": self._normalize_message(record.msg),
        }
        return json.dumps(log_record, ensure_ascii = False)

    def _normalize_message(self, msg):
        """
        Normalize log message content to ensure JSON compatibility.

        Supported types:
            - dict (recursive normalization)
            - list (recursive normalization)
            - datetime (ISO-like string)
            - any other type (string conversion)

        Args:
            msg: Original log message

        Returns:
            JSON-safe representation of the message
        """

        if isinstance(msg, dict):
            return {k: self._normalize_message(v) for k, v in msg.items()}

        if isinstance(msg, list):
            return [self._normalize_message(item) for item in msg]

        if isinstance(msg, datetime):
            return msg.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        return str(msg)

class Log(object):
    """
    Application logging manager.

    This class configures and exposes a structured logger with:
        - Rotating file output
        - Console output
        - Optional MySQL log persistence
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the logging manager.

        Args:
            config (dict): Application configuration dictionary
        """

        self.config = config
        self.logger = logging.getLogger(self.config['name'])
        self.init()

    def init(self) -> None:
        """
        Initialize logger handlers and formatters.

        This method configures:
            - Log level
            - Rotating file handler
            - Console handler
            - JSON formatter
        """

        ## determine log level
        try:
            log_level = getattr(logging, self.config['log']['level'])

        except Exception:
            log_level = logging.NOTSET

        self.logger.setLevel(log_level)

        ## file handler
        fh = RotatingFileHandler(
            filename=self.config['log']['file'],
            mode='a',
            maxBytes=int(self.config['log']['rotate']['max_size']) * 1024 * 1024 * 1024,
            backupCount=int(self.config['log']['rotate']['backup_count']),
        )
        fh.setLevel(log_level)

        ## console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level)

        ## add formatter
        fh.setFormatter(_JsonFormatter())
        ch.setFormatter(_JsonFormatter())

        # attach handlers
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        return None

    def add_mysql_handler(self, MySQLObj: object, table: str) -> bool:
        """
        Dynamically attach a MySQL logging handler.

        This method is safe to call multiple times and prevents
        duplicate MySQL handlers from being added.

        Args:
            MySQLObj (object): Initialized MySQL connection object

        Returns:
            bool: True if handler is attached or already exists
        """

        if not MySQLObj:
            return False
    
        # avoid adding duplicate MySQL handler
        for h in self.logger.handlers:
            if isinstance(h, _MySQLLogHandler):
                return True
    
        mh = _MySQLLogHandler(MySQLObj, table)
    
        # use same log level and formatter as existing handlers
        mh.setLevel(self.logger.level)
        if self.logger.handlers:
            mh.setFormatter(self.logger.handlers[0].formatter)
    
        self.logger.addHandler(mh)
        return True
    
