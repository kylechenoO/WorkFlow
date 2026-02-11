"""
WorkFlow Django Site Package

This module initializes the Django project and configures
PyMySQL as the MySQL database backend adapter.
"""

## use pymysql as MySQLdb adapter
import pymysql
pymysql.install_as_MySQLdb()
