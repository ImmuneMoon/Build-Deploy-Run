# workers/run_command.py

import logging
import subprocess

logger = logging.getLogger(__name__)


def run_command(command, cwd=None, shell=False, timeout=None, log_output=True, check=True):
    """
    Runs a subprocess command and logs its output.

    Args:
        command (list or str): The command to run.
        cwd (Path or str, optional): Directory to run the command from.
        shell (bool): Whether to run through the shell.
        timeout (int or float, optional): Timeout in seconds.
        log_output (bool): Whether to log stdout/stderr.
        check (bool): If True, raise RuntimeError on a non-zero exit code.
                      If False, return the CompletedProcess and let the caller inspect returncode.

    Returns:
        subprocess.CompletedProcess

    Raises:
        RuntimeError if check is True and the command fails.
    """
    display = " ".join(str(c) for c in command) if isinstance(command, (list, tuple)) else str(command)
    logger.info(f"Running command: {display}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=shell,
            timeout=timeout,
        )
    except Exception as e:
        logger.exception(f"Unexpected error running command: {e}")
        raise

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode == 0:
        if log_output:
            if stdout:
                logger.debug(f"Command STDOUT:\n{stdout}")
            if stderr:
                logger.debug(f"Command STDERR:\n{stderr}")
        return result

    logger.error(f"Command failed with return code {result.returncode}: {display}")
    logger.error(f"STDOUT:\n{stdout or 'None'}")
    logger.error(f"STDERR:\n{stderr or 'None'}")
    if check:
        raise RuntimeError(f"Command '{display}' failed with exit code {result.returncode}.")
    return result
