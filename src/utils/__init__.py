"""Utility package."""

from src.utils.logger import get_logger, suppress_uvicorn_access_logs

__all__ = ["get_logger", "suppress_uvicorn_access_logs"]
