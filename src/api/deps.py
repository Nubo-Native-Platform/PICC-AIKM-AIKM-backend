"""Shared API dependencies (NEW)."""

from fastapi import Request

from src.config.settings import settings


def current_user(request: Request) -> str:
    """Resolve the acting user from the PORTAL header (created_by / updated_by).

    Falls back to the X-User-Name header, then the configured default. Mirrors
    the header contract used by the React app's ApiService.
    """
    return (
        request.headers.get(settings.user_header)
        or request.headers.get("X-User-Name")
        or settings.default_user
    )
