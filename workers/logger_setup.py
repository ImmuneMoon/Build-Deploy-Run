# workers/logger_setup.py

import logging
from pathlib import Path


def setup_logger(name=None, log_file=None, level=logging.DEBUG):
    """
    Configure a logger with a console handler and an optional file handler.

    Pass name=None (or "") to configure the ROOT logger, so that every module logger
    (for example workers.run_command) propagates into the same console and file output.
    """
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    logger = logging.getLogger(name or None)
    logger.setLevel(level)

    # Avoid duplicate handlers if called twice.
    for h in list(logger.handlers):
        logger.removeHandler(h)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
