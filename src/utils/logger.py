"""Logging configuration.

INHERITED verbatim (apart from the settings import path) from
ai-sql-query-observability-service/src/utils/logger.py. Stdlib logging with a
console handler and a filter to silence /health access-log noise.
"""

import logging
import sys
from typing import Iterable, Optional

from src.config.settings import settings


class PathSuppressingFilter(logging.Filter):
    """Suppress access-log records for selected request paths."""

    def __init__(self, paths: Iterable[str]):
        super().__init__()
        self._paths = tuple(paths)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(f" {path} " in message for path in self._paths)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get or create a configured logger instance."""
    logger = logging.getLogger(name or __name__)

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def suppress_uvicorn_access_logs(paths: Iterable[str]) -> None:
    """Hide noisy uvicorn access logs for selected endpoints."""
    access_logger = logging.getLogger("uvicorn.access")
    if any(isinstance(f, PathSuppressingFilter) for f in access_logger.filters):
        return
    access_logger.addFilter(PathSuppressingFilter(paths))
