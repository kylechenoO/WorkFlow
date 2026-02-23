"""
SSH Workflow Procedure Module

This module defines the Ssh procedure class used by the workflow
engine for remote command execution and file transfer operations.
The class methods are invoked dynamically by the Flow engine
during workflow execution.

Responsibilities:
    - Establish and close SSH connections
    - Execute remote shell commands with stdout/stderr capture
    - Run local scripts on remote servers via stdin
    - Upload and download files via SFTP
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import paramiko

class Ssh(object):
    """
    SSH remote command execution and SFTP file transfer manager.

    Responsibilities:
        - Establish and close SSH connections
        - Execute remote shell commands
        - Run local scripts on remote servers
        - Upload and download files via SFTP
    """

    ## context keys
    _CTX_CON  = '__ssh_con__'
    _CTX_SFTP = '__ssh_sftp__'

    def __init__(self, logger: object) -> None:
        """
        Initialize the Ssh manager.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    def _get_con(self, context: dict):
        """Return the SSH client from context, or None."""
        return context.get(self._CTX_CON)

    def _get_sftp(self, context: dict):
        """Return the SFTP session from context, or None."""
        return context.get(self._CTX_SFTP)

    ## def connect(self, host: str, port: int, username: str, password: str, key_file: str, timeout: int) -> dict:
    def connect(self, context: dict, cfgs: dict) -> dict:
        """
        Establish an SSH connection to a remote server.

        Args:
            host (str): Remote server hostname or IP, @sys.ssh_key to use the system ssh_key on workflow (default: @sys.ssh_key)
            port (int): Optional SSH port (default: 22)
            username (str): SSH username
            password (str): Optional SSH password (default: "")
            key_file (str): Optional path to private key file (default: "")
            timeout (int): Optional connection timeout in seconds (default: 30)

        Returns:
            dict: Connection status
        """

        ## load args
        host = cfgs['host']
        port = int(cfgs.get('port', 22))
        username = cfgs['username']
        password = cfgs.get('password', None)
        key_file = cfgs.get('key_file', None)
        timeout = int(cfgs.get('timeout', 30))

        ## debug prt (never log password or key_file)
        self.logger.debug({'ssh.host': host})
        self.logger.debug({'ssh.port': port})
        self.logger.debug({'ssh.username': username})
        self.logger.debug({'ssh.timeout': timeout})

        try:
            ## create SSH client
            con = paramiko.SSHClient()
            con.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ## build connect kwargs
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': timeout
            }

            ## set auth method
            if key_file:
                pkey = paramiko.RSAKey.from_private_key_file(key_file)
                connect_kwargs['pkey'] = pkey

            if password:
                connect_kwargs['password'] = password

            ## connect
            con.connect(**connect_kwargs)

            ## open SFTP session
            sftp = con.open_sftp()

            context[self._CTX_CON] = con
            context[self._CTX_SFTP] = sftp

            self.logger.info({'status': 'Successfully connected to %s:%s as %s' % (host, port, username)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error connecting to SSH %s:%s: %s' % (host, port, e)})
            context[self._CTX_CON] = None
            context[self._CTX_SFTP] = None
            return {
                'status': False
            }

    ## def disconnect(self) -> dict:
    def disconnect(self, context: dict, cfgs: dict) -> dict:
        """
        Close the SSH and SFTP connections.

        This method is safe to call multiple times.
        """

        try:
            ## close SFTP
            sftp = self._get_sftp(context)
            if sftp:
                sftp.close()
                self.logger.info({'status': 'SFTP session closed successfully'})

            ## close SSH
            con = self._get_con(context)
            if con:
                con.close()
                self.logger.info({'status': 'SSH connection closed successfully'})

            context[self._CTX_SFTP] = None
            context[self._CTX_CON] = None

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error disconnecting from SSH: %s' % (e)})

        return {
            'status': True
        }

    ## def run(self, cmd: str, timeout: int) -> dict:
    def run(self, context: dict, cfgs: dict) -> dict:
        """
        Execute a remote shell command.

        Args:
            cmd (str): Shell command to execute
            timeout (int): Optional command timeout in seconds (default: 30)

        Returns:
            dict: Command result with exit_code, stdout, stderr
        """

        ## load args
        cmd = cfgs['cmd']
        timeout = int(cfgs.get('timeout', 30))

        ## debug prt
        self.logger.debug({'ssh.cmd': cmd})
        self.logger.debug({'ssh.timeout': timeout})

        try:
            ## check connection
            con = self._get_con(context)
            if not con:
                self.logger.error({'status': 'Error: No active SSH connection. Please connect first.'})
                return {
                    'status': False,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': ''
                }

            ## execute command
            stdin, stdout, stderr = con.exec_command(cmd, timeout=timeout)

            ## read output
            stdout_str = stdout.read().decode('utf-8', errors='replace')
            stderr_str = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            self.logger.info({'status': 'Command executed with exit_code=%s' % (exit_code)})
            return {
                'status': exit_code == 0,
                'exit_code': exit_code,
                'stdout': stdout_str,
                'stderr': stderr_str
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error executing command: %s' % (e)})
            return {
                'status': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }

    ## def run_script(self, script_path: str, interpreter: str, args: str, timeout: int) -> dict:
    def run_script(self, context: dict, cfgs: dict) -> dict:
        """
        Run a local script on a remote server without uploading.

        Reads the local script content and feeds it to the remote
        interpreter via stdin.

        Args:
            script_path (str): Local path to script file
            interpreter (str): Optional remote interpreter (default: "bash")
            args (str): Optional arguments to pass to the script (default: "")
            timeout (int): Optional command timeout in seconds (default: 30)

        Returns:
            dict: Script result with exit_code, stdout, stderr
        """

        ## load args
        script_path = cfgs['script_path']
        interpreter = cfgs.get('interpreter', 'bash')
        args = cfgs.get('args', '')
        timeout = int(cfgs.get('timeout', 30))

        ## debug prt
        self.logger.debug({'ssh.script_path': script_path})
        self.logger.debug({'ssh.interpreter': interpreter})
        self.logger.debug({'ssh.args': args})
        self.logger.debug({'ssh.timeout': timeout})

        try:
            ## check connection
            con = self._get_con(context)
            if not con:
                self.logger.error({'status': 'Error: No active SSH connection. Please connect first.'})
                return {
                    'status': False,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': ''
                }

            ## read local script content
            try:
                with open(script_path, 'r') as f:
                    script_content = f.read()
            except FileNotFoundError:
                self.logger.error({'status': 'Error: Script file not found: %s' % (script_path)})
                return {
                    'status': False,
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': 'Script file not found: %s' % script_path
                }

            ## build remote command
            remote_cmd = '%s %s' % (interpreter, args) if args else interpreter

            ## execute with script content via stdin
            stdin, stdout, stderr = con.exec_command(remote_cmd, timeout=timeout)
            stdin.write(script_content)
            stdin.channel.shutdown_write()

            ## read output
            stdout_str = stdout.read().decode('utf-8', errors='replace')
            stderr_str = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()

            self.logger.info({'status': 'Script %s executed with exit_code=%s' % (script_path, exit_code)})
            return {
                'status': exit_code == 0,
                'exit_code': exit_code,
                'stdout': stdout_str,
                'stderr': stderr_str
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error executing script %s: %s' % (script_path, e)})
            return {
                'status': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }

    ## def upload(self, local_path: str, remote_path: str) -> dict:
    def upload(self, context: dict, cfgs: dict) -> dict:
        """
        Upload a local file to the remote server via SFTP.

        Args:
            local_path (str): Local file path
            remote_path (str): Remote destination path

        Returns:
            dict: Upload result
        """

        ## load args
        local_path = cfgs['local_path']
        remote_path = cfgs['remote_path']

        ## debug prt
        self.logger.debug({'ssh.local_path': local_path})
        self.logger.debug({'ssh.remote_path': remote_path})

        try:
            ## check connection
            sftp = self._get_sftp(context)
            if not sftp:
                self.logger.error({'status': 'Error: No active SFTP session. Please connect first.'})
                return {
                    'status': False
                }

            ## upload file
            sftp.put(local_path, remote_path)

            self.logger.info({'status': 'Successfully uploaded %s to %s' % (local_path, remote_path)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error uploading file: %s' % (e)})
            return {
                'status': False
            }

    ## def download(self, remote_path: str, local_path: str) -> dict:
    def download(self, context: dict, cfgs: dict) -> dict:
        """
        Download a remote file to the local machine via SFTP.

        Args:
            remote_path (str): Remote file path
            local_path (str): Local destination path

        Returns:
            dict: Download result
        """

        ## load args
        remote_path = cfgs['remote_path']
        local_path = cfgs['local_path']

        ## debug prt
        self.logger.debug({'ssh.remote_path': remote_path})
        self.logger.debug({'ssh.local_path': local_path})

        try:
            ## check connection
            sftp = self._get_sftp(context)
            if not sftp:
                self.logger.error({'status': 'Error: No active SFTP session. Please connect first.'})
                return {
                    'status': False
                }

            ## download file
            sftp.get(remote_path, local_path)

            self.logger.info({'status': 'Successfully downloaded %s to %s' % (remote_path, local_path)})
            return {
                'status': True
            }

        ## error handling
        except Exception as e:
            self.logger.error({'status': 'Error downloading file: %s' % (e)})
            return {
                'status': False
            }
