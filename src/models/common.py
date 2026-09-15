"""Shared models (NEW)."""

from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error envelope — mirrors the ingestion service's {detail, request_id}."""

    detail: str
    request_id: Optional[str] = None
