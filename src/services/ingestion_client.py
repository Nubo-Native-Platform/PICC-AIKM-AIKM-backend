"""Client for the (separate) ingestion service (NEW).

createBucketDetails / re-ingest call request_ingestion() as a background task;
the ingestion service is expected to POST results back to
/manageBucketDetails/ingestionCallback. Soft-delete calls request_delete_by_source().

Until the async ingestion + delete_by_source HTTP endpoints exist on the
ingestion service, set INGESTION_ENABLED=false (default): the document is left
in status PENDING and this client just logs.
"""

import httpx

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def request_ingestion(detail_id: str, payload: dict) -> None:
    if not settings.ingestion_enabled or not settings.ingestion_service_url:
        logger.info("[ingestion disabled] detail=%s — status stays PENDING", detail_id)
        return

    body = {
        "detail_id": detail_id,
        "document": payload,
        "callback_url": f"{settings.callback_base_url}/manageBucketDetails/ingestionCallback",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            resp = await client.post(settings.ingestion_service_url, json=body)
            resp.raise_for_status()
        logger.info("[ingestion requested] detail=%s", detail_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[ingestion request failed] detail=%s: %s", detail_id, exc)


async def request_delete_by_source(source_id: str) -> None:
    if not settings.ingestion_enabled or not settings.ingestion_delete_url:
        logger.info("[ingestion delete disabled] source=%s", source_id)
        return
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            resp = await client.post(settings.ingestion_delete_url, json={"source_id": source_id})
            resp.raise_for_status()
        logger.info("[delete_by_source requested] source=%s", source_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[delete_by_source failed] source=%s: %s", source_id, exc)
