# install_config/install_workers/subprocess_utils.py
import subprocess
import logging
import traceback

logger = logging.getLogger(__name__)

def run_command(cmd, env=None, cwd=None):
    if not cmd:
        raise ValueError("Command is empty or None.")
    if isinstance(cmd, str):
        cmd = [cmd]
    elif not isinstance(cmd, (list, tuple)):
        raise TypeError("Command must be a string or list of strings.")
    for i, part in enumerate(cmd):
        if not isinstance(part, str):
            raise TypeError(f"Command part at index {i} is not a string: {repr(part)}")

    logger.info(f"[CMD] Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env, cwd=cwd)
        if result.stdout:
            logger.info(result.stdout.strip())
        if result.stderr:
            logger.warning(result.stderr.strip())
    except subprocess.CalledProcessError as e:
        logger.error(f"[ERROR] Command failed: {e}")
        logger.error(f"[STDOUT]\n{e.stdout}")
        logger.error(f"[STDERR]\n{e.stderr}")
        raise
    except Exception as e:
        logger.error(f"[FATAL] Unexpected error: {e}")
        logger.error(traceback.format_exc())
        raise
