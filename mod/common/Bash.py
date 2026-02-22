"""
Bash Workflow Procedure Module

This module defines the Bash procedure class used by the workflow
engine for local shell command execution. The class methods are invoked
dynamically by the Flow engine during workflow execution.

Responsibilities:
    - Execute shell commands and return stdout, stderr, exit_code
    - Support custom working directory and environment variables
    - Support configurable timeout

Security note:
    shell=True is the default for run() to support piped and compound commands.
    Avoid passing untrusted user input directly as cmd when shell=True, as this
    can lead to shell injection. Use shell=False and a list for cmd when the
    command arguments come from external input.
"""

## version related
__author__ = "Kyle"
__version__ = "0.0.2"
__email__ = "kyle@hacking-linux.com"

## import buildin pkgs
import os
import subprocess


class Bash(object):
    """
    Local shell command executor.

    Responsibilities:
        - Run shell commands with configurable timeout and environment
        - Return structured results with exit_code, stdout, stderr
    """

    def __init__(self, logger: object) -> None:
        """
        Initialize the Bash executor.

        Args:
            logger (object): Logger instance for debug and error reporting
        """

        self.logger = logger

    ## def run(self, cmd, cwd, env, timeout, shell) -> dict:
    def run(self, context: dict, cfgs: dict) -> dict:
        """
        Execute a shell command.

        Args:
            cmd (str or list): Command to execute. Use a string for shell commands (pipes, redirects, compound commands). Use a list for safe argument passing when shell=False.
            cwd (str): Optional working directory (default: current directory)
            env (dict): Optional environment variables merged with the current environment
            timeout (int): Timeout in seconds (default: 60)
            shell (bool): Use shell interpretation (default: True). Set to False when passing cmd as a list with untrusted arguments.

        Returns:
            dict: Execution result with exit_code, stdout, stderr, and status
                  status is True only when exit_code is 0
        """

        ## load args
        cmd = cfgs['cmd']
        cwd = cfgs.get('cwd', '/')
        env_extra = cfgs.get('env', None)
        timeout = int(cfgs.get('timeout', 60))
        shell = cfgs.get('shell', True)

        ## debug prt (log only first 200 chars to avoid leaking secrets)
        cmd_preview = str(cmd)[:200] if cmd else ''
        self.logger.debug({'bash.cmd_preview': cmd_preview})
        self.logger.debug({'bash.cwd': cwd})
        self.logger.debug({'bash.timeout': timeout})
        self.logger.debug({'bash.shell': shell})

        try:
            ## build environment
            env = os.environ.copy()
            if env_extra:
                env.update(env_extra)

            ## execute command
            proc = subprocess.run(
                cmd,
                shell=shell,
                cwd=cwd,
                env=env,
                timeout=timeout,
                capture_output=True,
                text=True
            )

            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
            status = (exit_code == 0)

            if status:
                self.logger.info({'status': 'Command completed with exit_code %s' % (exit_code)})
            else:
                self.logger.error({'status': 'Command failed with exit_code %s: %s' % (exit_code, stderr[:200])})

            return {
                'status': status,
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr
            }

        ## error handling
        except subprocess.TimeoutExpired as e:
            self.logger.error({'status': 'Command timed out after %s seconds: %s' % (timeout, e)})
            return {
                'status': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': 'Timeout after %s seconds' % timeout
            }

        except Exception as e:
            self.logger.error({'status': 'Error executing command: %s' % (e)})
            return {
                'status': False,
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
