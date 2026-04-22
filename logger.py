import logging
import os
from datetime import datetime

import pytz

import config


def _ist_time(*args):
    ist = pytz.timezone(config.TIMEZONE)
    return datetime.now(ist).timetuple()


def setup_logger(name: str = "trading") -> logging.Logger:
    os.makedirs(config.LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    formatter.converter = _ist_time

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler – daily rotating log file
    ist = pytz.timezone(config.TIMEZONE)
    today = datetime.now(ist).strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(config.LOG_DIR, f"trading_{today}.log"),
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Separate error log
    error_handler = logging.FileHandler(
        os.path.join(config.LOG_DIR, f"errors_{today}.log"),
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger
