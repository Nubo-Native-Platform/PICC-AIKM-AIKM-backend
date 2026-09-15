"""Client for the (separate) Milvus collection provisioning service (NEW).

createBucket calls request_provision() as a fire-and-forget background task.
The provisioning service is expected to create a Milvus collection named after
the bucket and then POST the result back to /manageBucket/provisionCallback.

Until that service exists, set PROVISION_ENABLED=false (default): the bucket is
left in status PROVISIONING and this client just logs. Flip the flag and set
PROVISION_SERVICE_URL once the provisioning service is available.
"""

import httpx

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def request_delete(bucket_id: str, collection_name: str) -> None:
    if not settings.provision_enabled or not settings.provision_delete_url:
        logger.info(
            "[provision delete disabled] bucket=%s collection=%s — Milvus collection not removed",
            bucket_id, collection_name,
        )
        return
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            resp = await client.post(
                settings.provision_delete_url,
                json={"bucket_id": bucket_id, "collection_name": collection_name},
            )
            resp.raise_for_status()
        logger.info("[provision delete requested] bucket=%s collection=%s", bucket_id, collection_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("[provision delete failed] bucket=%s: %s", bucket_id, exc)


async def request_provision(bucket_id: str, collection_name: str) -> None:
    if not settings.provision_enabled or not settings.provision_service_url:
        logger.info(
            "[provision disabled] bucket=%s collection=%s — status stays PROVISIONING",
            bucket_id, collection_name,
        )
        return

    payload = {
        "bucket_id": bucket_id,
        "collection_name": collection_name,
        "callback_url": f"{settings.callback_base_url}/manageBucket/provisionCallback",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            resp = await client.post(settings.provision_service_url, json=payload)
            resp.raise_for_status()
        logger.info("[provision requested] bucket=%s collection=%s", bucket_id, collection_name)
    except Exception as exc:  # noqa: BLE001 - background task, must not crash the app
        logger.error("[provision request failed] bucket=%s: %s", bucket_id, exc)
