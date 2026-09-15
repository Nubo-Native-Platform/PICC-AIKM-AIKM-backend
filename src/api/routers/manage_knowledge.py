from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from typing import List, Optional
from urllib.parse import urlencode


from src.config.settings import settings
from src.repositories import model_details_repo
from src.services import minio_storage
from src.utils.logger import get_logger

logger = get_logger(__name__)

MANAGE_KNOWLEDGE_PREFIX = "/manageKnowledge"

router = APIRouter(
    prefix=MANAGE_KNOWLEDGE_PREFIX,
    tags=["manageKnowledge"],
)


class SearchRequest(BaseModel):
    question: str
    limit: Optional[int] = Field(default=None, ge=1)
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extend_public: Optional[bool] = None
    bucket_names: Optional[List[str]] = None


def _manage_knowledge_base_path() -> str:
    return f"/nnp-km-backend-local-llm{MANAGE_KNOWLEDGE_PREFIX}"


def _rewrite_image_urls(response_data: dict) -> dict:
    images = response_data.get("images")
    if not isinstance(images, list):
        return response_data

    asset_path = f"{_manage_knowledge_base_path()}/assets/image"
    for image in images:
        if not isinstance(image, dict):
            continue
        object_key = image.get("object_key")
        bucket = image.get("bucket") or settings.minio_bucket
        if not object_key or not bucket:
            continue
        image["bucket"] = bucket
        image["url"] = f"{asset_path}?{urlencode({'bucket': bucket, 'object_key': object_key})}"
    return response_data


@router.get("/assets/image")
def get_asset_image(bucket: str, object_key: str):
    try:
        response = minio_storage.get_image_asset(bucket, object_key)
    except Exception as exc:  # noqa: BLE001
        logger.error("[get_asset_image] failed bucket=%s object_key=%s: %s", bucket, object_key, exc)
        raise HTTPException(status_code=404, detail="Image asset not found") from exc

    content_type = response.headers.get("content-type") or "application/octet-stream"
    return StreamingResponse(
        minio_storage.iter_minio_object(response),
        media_type=content_type,
    )


@router.post("/search")
async def search_knowledge(
    payload: SearchRequest,
    request: Request,
):
    """Proxy to ai-rag-query-service."""
    logger.info(f"[{request.state.request_id}] Payload received for knowledge base search api: {payload}")
    try:
        model_type = (
            "local"
            if (settings.model_type or "").strip().lower() == "local"
            else "public"
        )
        try:
            model_details = await run_in_threadpool(
                model_details_repo.get_active_text_model,
                model_type,
            )
        except Exception:
            logger.exception(
                "[%s] Model details lookup failed; continuing without model credentials",
                request.state.request_id,
            )
            model_details = None

        timeout = (
            settings.get_summary_timeout_local
            if model_type == "local"
            else settings.get_summary_timeout_public
        )

        rag_payload = {
            "question": payload.question,
            "collectionNames": payload.bucket_names or [],
            "sourceCount": payload.limit if payload.limit is not None else 3,
            "similarityThreshold": (
                payload.similarity_threshold
                if payload.similarity_threshold is not None
                else 0.0
            ),
            "extendPublicInfo": (
                payload.extend_public
                if payload.extend_public is not None
                else False
            ),
            "modelType": model_type,
        }
        if model_details and model_details.get("ModelName") is not None:
            rag_payload["ModelName"] = model_details["ModelName"]
        if model_details and model_details.get("API_Key") is not None:
            rag_payload["APIKey"] = model_details["API_Key"]

        async with httpx.AsyncClient(timeout=timeout) as client:
            # -------below version ONLY accepts user question------
            # resp = await client.post(
            #     f"{settings.rag_query_service_url}/ask",
            #     json={"question": payload.question},
            # )
            resp = await client.post(
                f"{settings.rag_query_service_url}/ask",
                json=rag_payload,
            )
            resp.raise_for_status()
            return _rewrite_image_urls(resp.json())
    except httpx.HTTPError as exc:
        logger.error("[search_knowledge] failed: %s", exc)
        return {"answer": [], "error": str(exc)}
