"""
Notify Workflow Procedure Module

This module defines the Notify procedure class used by the workflow
engine for notification operations. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Send email notifications via SMTP
    - Send webhook notifications to Slack, Teams, DingTalk, etc.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.1"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

class Notify(object):
    """
    Notification manager for workflow procedures.

    Responsibilities:
        - Send email via SMTP with TLS support
        - Send webhook POST to any URL (Slack, Teams, DingTalk, etc.)
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the Notify manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    ## def email(self, smtp_host: str, smtp_port: int, username: str, password: str, from_addr: str, to_addrs: list, subject: str, body: str, body_type: str, cc: list, use_tls: bool) -> dict:
    def email(self, context: dict, cfgs: dict) -> dict:
        """
        Send an email via SMTP.

        Args:
            smtp_host (str): SMTP server hostname
            smtp_port (int): SMTP server port
            username (str): Optional SMTP login username
            password (str): Optional SMTP login password
            from_addr (str): Sender email address
            to_addrs (list): List of recipient email addresses
            subject (str): Email subject
            body (str): Email body content
            body_type (str): Optional body MIME type (plain or html), default plain
            cc (list): Optional list of CC email addresses
            use_tls (bool): Optional use STARTTLS, default True

        Returns:
            dict: Send result
        """

        ## load args
        smtp_host = cfgs['smtp_host']
        smtp_port = int(cfgs['smtp_port'])
        username = cfgs.get('username', None)
        password = cfgs.get('password', None)
        from_addr = cfgs['from_addr']
        to_addrs = cfgs['to_addrs']
        subject = cfgs['subject']
        body = cfgs['body']
        body_type = cfgs.get('body_type', 'plain')
        cc = cfgs.get('cc', [])
        use_tls = cfgs.get('use_tls', True)

        ## debug prt (never log password)
        self.logger.debug({'notify.smtp_host': smtp_host})
        self.logger.debug({'notify.smtp_port': smtp_port})
        self.logger.debug({'notify.from_addr': from_addr})
        self.logger.debug({'notify.to_addrs': to_addrs})
        self.logger.debug({'notify.subject': subject})
        self.logger.debug({'notify.body_type': body_type})
        self.logger.debug({'notify.use_tls': use_tls})

        server = None
        try:
            ## build email message
            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_addrs)
            msg['Subject'] = subject

            ## set CC header
            if cc:
                msg['Cc'] = ', '.join(cc)

            ## attach body
            msg.attach(MIMEText(body, body_type))

            ## build recipient list
            all_recipients = list(to_addrs) + list(cc)

            ## connect to SMTP server
            server = smtplib.SMTP(smtp_host, smtp_port)

            ## start TLS
            if use_tls:
                server.starttls()

            ## login if credentials provided
            if username and password:
                server.login(username, password)

            ## send email
            server.sendmail(from_addr, all_recipients, msg.as_string())

            self.logger.info({'status': 'Successfully sent email to %s' % (to_addrs)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error sending email: %s' % (e)})
            return {
                'status': False
            }

        finally:
            ## ensure server connection is closed
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    ## def webhook(self, url: str, method: str, headers: dict, body: dict, timeout: int) -> dict:
    def webhook(self, context: dict, cfgs: dict) -> dict:
        """
        Send a webhook notification.

        Args:
            url (str): Webhook URL
            method (str): Optional HTTP method, default POST
            headers (dict): Optional request headers
            body (dict): Request body (sent as JSON)
            timeout (int): Optional request timeout in seconds, default 30

        Returns:
            dict: Send result
        """

        ## load args
        url = cfgs['url']
        method = cfgs.get('method', 'POST')
        headers = cfgs.get('headers', {})
        body = cfgs['body']
        timeout = int(cfgs.get('timeout', 30))

        ## debug prt
        self.logger.debug({'notify.webhook_url': url})
        self.logger.debug({'notify.webhook_method': method})
        self.logger.debug({'notify.webhook_timeout': timeout})

        try:
            ## send webhook request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=timeout
            )

            ## check response status
            status = response.status_code >= 200 and response.status_code < 300

            if not status:
                self.logger.error({'status': 'Webhook returned status code %s' % (response.status_code)})

            self.logger.info({'status': 'Webhook %s %s returned %s' % (method, url, response.status_code)})
            return {
                'status': status
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error sending webhook: %s' % (e)})
            return {
                'status': False
            }
