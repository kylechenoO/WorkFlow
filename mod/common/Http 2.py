"""
HTTP Workflow Procedure Module

This module defines the Http procedure class used by the workflow
engine for HTTP client operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Send HTTP GET, POST, PUT, DELETE requests
    - Support JSON and form data request bodies
    - Support basic authentication and custom headers
    - Parse JSON responses with text fallback
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import requests
from requests.auth import HTTPBasicAuth

class Http(object):
    """
    HTTP client for workflow procedures.

    Responsibilities:
        - Send HTTP requests (GET, POST, PUT, DELETE)
        - Support JSON body, form data, basic auth
        - Parse responses and return structured results
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the Http manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _request(self, http_method: str, cfgs: dict) -> dict:
        """
        Internal helper to execute an HTTP request.

        Args:
            http_method (str): HTTP method (GET, POST, PUT, DELETE)
            cfgs (dict): Request configuration parameters

        Returns:
            dict: Request result with status_code, data, headers
        """

        ## load args
        url = cfgs['url']
        headers = cfgs.get('headers', {})
        params = cfgs.get('params', {})
        json_body = cfgs.get('json', None)
        form_data = cfgs.get('data', None)
        timeout = int(cfgs.get('timeout', 30))
        auth = cfgs.get('auth', None)
        verify_ssl = cfgs.get('verify_ssl', True)

        ## debug prt
        self.logger.debug({'http.method': http_method})
        self.logger.debug({'http.url': url})
        self.logger.debug({'http.timeout': timeout})
        self.logger.debug({'http.verify_ssl': verify_ssl})

        try:
            ## build request kwargs
            kwargs = {
                'url': url,
                'headers': headers,
                'params': params,
                'timeout': timeout,
                'verify': verify_ssl
            }

            ## set auth if provided
            if auth:
                kwargs['auth'] = HTTPBasicAuth(auth['username'], auth['password'])

            ## set body for POST/PUT (json takes precedence over form data)
            if json_body is not None:
                kwargs['json'] = json_body
            elif form_data is not None:
                kwargs['data'] = form_data

            ## execute request
            response = requests.request(http_method, **kwargs)

            ## parse response body
            try:
                response_data = response.json()
            except Exception:
                response_data = response.text

            ## determine status
            status = response.status_code >= 200 and response.status_code < 300

            self.logger.info({'status': 'HTTP %s %s returned %s' % (http_method, url, response.status_code)})
            return {
                'status': status,
                'status_code': response.status_code,
                'data': response_data,
                'headers': dict(response.headers)
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error in HTTP %s %s: %s' % (http_method, url, e)})
            return {
                'status': False,
                'status_code': 0,
                'data': None,
                'headers': {}
            }

    ## def get(self, url: str, headers: dict, params: dict, timeout: int, auth: dict, verify_ssl: bool) -> dict:
    def get(self, context: dict, cfgs: dict) -> dict:
        """
        Send an HTTP GET request.

        Args:
            url (str): Target URL
            headers (dict): Optional request headers
            params (dict): Optional query string parameters
            timeout (int): Optional request timeout in seconds
            auth (dict): Optional basic auth with username/password
            verify_ssl (bool): Optional SSL certificate verification

        Returns:
            dict: Request result with status_code, data, headers
        """

        return self._request('GET', cfgs)

    ## def post(self, url: str, headers: dict, params: dict, json: dict, data: dict, timeout: int, auth: dict, verify_ssl: bool) -> dict:
    def post(self, context: dict, cfgs: dict) -> dict:
        """
        Send an HTTP POST request.

        Args:
            url (str): Target URL
            headers (dict): Optional request headers
            params (dict): Optional query string parameters
            json (dict): Optional JSON body
            data (dict): Optional form data body
            timeout (int): Optional request timeout in seconds
            auth (dict): Optional basic auth with username/password
            verify_ssl (bool): Optional SSL certificate verification

        Returns:
            dict: Request result with status_code, data, headers
        """

        return self._request('POST', cfgs)

    ## def put(self, url: str, headers: dict, params: dict, json: dict, data: dict, timeout: int, auth: dict, verify_ssl: bool) -> dict:
    def put(self, context: dict, cfgs: dict) -> dict:
        """
        Send an HTTP PUT request.

        Args:
            url (str): Target URL
            headers (dict): Optional request headers
            params (dict): Optional query string parameters
            json (dict): Optional JSON body
            data (dict): Optional form data body
            timeout (int): Optional request timeout in seconds
            auth (dict): Optional basic auth with username/password
            verify_ssl (bool): Optional SSL certificate verification

        Returns:
            dict: Request result with status_code, data, headers
        """

        return self._request('PUT', cfgs)

    ## def delete(self, url: str, headers: dict, params: dict, timeout: int, auth: dict, verify_ssl: bool) -> dict:
    def delete(self, context: dict, cfgs: dict) -> dict:
        """
        Send an HTTP DELETE request.

        Args:
            url (str): Target URL
            headers (dict): Optional request headers
            params (dict): Optional query string parameters
            timeout (int): Optional request timeout in seconds
            auth (dict): Optional basic auth with username/password
            verify_ssl (bool): Optional SSL certificate verification

        Returns:
            dict: Request result with status_code, data, headers
        """

        return self._request('DELETE', cfgs)
