# workers/ logger_setup.py

import logging
from pathlib import Path

def setup_logger(name=__name__, log_file=None, level=logging.DEBUG):
    """Setup a consistent logger."""
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Optional file handler
    file_handler = None
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(console_handler)
    if file_handler:
        logger.addHandler(file_handler)

    return logger
