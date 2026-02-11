"""
WorkFlow REST API Client

Wraps HTTP calls to the Flask REST API backend
for all workflow mutation operations.
"""

## import buildin pkgs
import logging

## import 3rd party pkgs
import requests

## import django pkgs
from django.conf import settings

logger = logging.getLogger(__name__)


class WorkflowAPIClient:
    """
    Client for communicating with the WorkFlow Flask REST API.

    All write operations (create, update, delete, enable, disable,
    rename, run) are routed through this client to the backend API.
    """

    def __init__(self):
        """Initialize the API client with the base URL from settings."""

        self.base_url = settings.WF_API_BASE_URL
        self.timeout = 30

    def _request(self, method, path, json_data=None):
        """
        Make an HTTP request to the Flask API.

        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            path (str): API endpoint path
            json_data (dict): Request body

        Returns:
            dict: API response data or error dict
        """

        url = '%s%s' % (self.base_url, path)

        try:
            resp = requests.request(
                method=method,
                url=url,
                json=json_data,
                timeout=self.timeout,
            )
            data = resp.json()

            if resp.status_code >= 400:
                logger.error({'status': 'API error %s %s: %s' % (method, path, data)})
                return {
                    'status': False,
                    'error': data.get('error', 'API returned %s' % resp.status_code),
                }

            return data

        except requests.exceptions.ConnectionError as e:
            logger.error({'status': 'API connection error: %s' % (e)})
            return {
                'status': False,
                'error': 'Cannot connect to WorkFlow API at %s' % self.base_url,
            }
        except requests.exceptions.Timeout as e:
            logger.error({'status': 'API timeout: %s' % (e)})
            return {
                'status': False,
                'error': 'API request timed out',
            }
        except Exception as e:
            logger.error({'status': 'API error: %s' % (e)})
            return {
                'status': False,
                'error': str(e),
            }

    def create_flow(self, name, procedures):
        """
        Create a new workflow.

        Args:
            name (str): Workflow name
            procedures (list): List of procedure step dicts

        Returns:
            dict: API response
        """

        return self._request('POST', '/flow', json_data={
            'name': name,
            'procedures': procedures,
        })

    def update_flow(self, name, procedures):
        """
        Update an existing workflow.

        Args:
            name (str): Workflow name
            procedures (list): Updated procedure step list

        Returns:
            dict: API response
        """

        return self._request('PUT', '/flow/%s' % name, json_data={
            'procedures': procedures,
        })

    def delete_flow(self, name):
        """
        Delete a workflow (soft delete).

        Args:
            name (str): Workflow name

        Returns:
            dict: API response
        """

        return self._request('DELETE', '/flow/%s' % name)

    def enable_flow(self, name):
        """
        Enable a workflow.

        Args:
            name (str): Workflow name

        Returns:
            dict: API response
        """

        return self._request('PUT', '/flow/%s/enable' % name)

    def disable_flow(self, name):
        """
        Disable a workflow.

        Args:
            name (str): Workflow name

        Returns:
            dict: API response
        """

        return self._request('PUT', '/flow/%s/disable' % name)

    def rename_flow(self, current, new):
        """
        Rename a workflow.

        Args:
            current (str): Current workflow name
            new (str): New workflow name

        Returns:
            dict: API response
        """

        return self._request('PUT', '/flow/%s/rename' % current, json_data={
            'new': new,
        })

    def run_flow(self, name):
        """
        Execute a workflow.

        Args:
            name (str): Workflow name

        Returns:
            dict: API response
        """

        return self._request('POST', '/flow/%s/run' % name)
