# workers/ run_command.py

import logging, subprocess


logger = logging.getLogger(__name__)

def run_command(command, cwd=None, shell=False, timeout=None, log_output=True):
    """
    Runs a subprocess command safely.
    
    Args:
        command (list or str): The command to run.
        cwd (Path or str, optional): Directory to run the command from.
        shell (bool): Whether to run through the shell.
        timeout (int or float, optional): Timeout in seconds.
        log_output (bool): Whether to log the output.

    Returns:
        CompletedProcess if success.
    
    Raises:
        RuntimeError if the command fails.
    """
    logger.info(f"Running command: {' '.join(command) if isinstance(command, list) else command}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            shell=shell,
            timeout=timeout
        )
        if log_output:
            logger.debug(f"Command STDOUT:\n{result.stdout.strip()}")
            logger.debug(f"Command STDERR:\n{result.stderr.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}")
        logger.error(f"STDOUT:\n{e.stdout.strip() if e.stdout else 'None'}")
        logger.error(f"STDERR:\n{e.stderr.strip() if e.stderr else 'None'}")
        raise RuntimeError(f"Command '{command}' failed.") from e
    except Exception as e:
        logger.exception(f"Unexpected error running command: {e}")
        raise