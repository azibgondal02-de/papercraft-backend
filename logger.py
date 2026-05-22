from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "educare"
_LOG_FILE = Path(__file__).resolve().parent / "app.log"


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    base_logger = _configure_logger()
    if name and name != _LOGGER_NAME:
        return base_logger.getChild(name)
    return base_logger


def log_info(message: str, *args, **kwargs) -> None:
    get_logger().info(message, *args, **kwargs)


def log_warning(message: str, *args, **kwargs) -> None:
    get_logger().warning(message, *args, **kwargs)


def log_error(message: str, *args, **kwargs) -> None:
    get_logger().error(message, *args, **kwargs)
