"""manageBucket router (NEW). Tables: nnp_km_buckets + nnp_account_bucket_map."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from src.api.deps import current_user
from src.config.settings import settings
from src.models.bucket import BucketCreate, BucketUpdate, ProvisionCallback
from src.repositories import bucket_detail_repo, bucket_repo
from src.services import milvus_client, minio_storage
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/manageBucket", tags=["manageBucket"])

def _embedding_dim(embedding_backend: str | None) -> int:
    return (
        settings.local_embedding_dimension
        if embedding_backend == "local"
        else settings.embedding_dimension
    )


async def _provision_bucket(bucket_id: str, bucket_name: str, embedding_backend: str | None = None) -> None:
    """Background task: create the Milvus collection and write the outcome back to Postgres."""
    try:
        ok, error_msg = await milvus_client.create_collection(
            bucket_name,
            dim=_embedding_dim(embedding_backend),
        )
        if ok:
            logger.info("[milvus create] success bucket=%s collection=%s", bucket_id, bucket_name)
            await run_in_threadpool(bucket_repo.set_provision_result, bucket_id, "ACTIVE", None)
        else:
            logger.error(
                "[milvus create] failed bucket=%s collection=%s: %s", bucket_id, bucket_name, error_msg
            )
            await run_in_threadpool(bucket_repo.set_provision_result, bucket_id, "FAILED", error_msg)
    except Exception as exc:  # noqa: BLE001
        logger.error("[provision background task error] bucket=%s: %s", bucket_id, exc)


async def _delete_milvus_collection(bucket_id: str, bucket_name: str) -> None:
    """Background task: drop the Milvus collection after the bucket row is soft-deleted."""
    try:
        ok, error_msg = await milvus_client.delete_collection(bucket_name)
        if ok:
            logger.info("[milvus delete] success bucket=%s collection=%s", bucket_id, bucket_name)
        else:
            logger.error(
                "[milvus delete] failed bucket=%s collection=%s: %s", bucket_id, bucket_name, error_msg
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("[milvus delete background task error] bucket=%s: %s", bucket_id, exc)


async def _delete_bucket_minio_assets(bucket_id: str, detail_ids: list[str]) -> None:
    """Background task: remove MinIO visual artifacts for all bucket details."""
    try:
        deleted = await run_in_threadpool(
            minio_storage.delete_documents_assets,
            detail_ids,
        )
        logger.info(
            "[minio bucket assets delete] bucket=%s prefixes_deleted=%d/%d",
            bucket_id,
            deleted,
            len(detail_ids),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[minio bucket assets delete error] bucket=%s: %s", bucket_id, exc)


@router.get("/getDetails/{account_id}")
async def get_details(account_id: str, includeDeleted: bool = False):
    """Return all buckets mapped to an account."""
    return await run_in_threadpool(bucket_repo.get_by_account, account_id, includeDeleted)


@router.get("/getAccountIds/{bucket_id}")
async def get_account_ids(bucket_id: str):
    """Return all account IDs associated with a bucket."""
    return await run_in_threadpool(bucket_repo.get_account_ids_by_bucket, bucket_id)


@router.post("/createBucket", status_code=status.HTTP_202_ACCEPTED)
async def create_bucket(payload: BucketCreate, request: Request, background_tasks: BackgroundTasks):
    """Create a bucket (status PROVISIONING) and launch direct Milvus collection creation.

    The background task updates status to ACTIVE on success or FAILED on error.
    Returns 202 immediately; status can be polled via getDetails.
    """
    user = current_user(request)
    bucket = await run_in_threadpool(bucket_repo.create, payload.model_dump(), user)
    background_tasks.add_task(
        _provision_bucket,
        str(bucket["id"]),
        bucket["bucket_name"],
        bucket.get("embedding_backend"),
    )
    return bucket


@router.put("/updateBucket/{bucket_id}")
async def update_bucket(bucket_id: str, payload: BucketUpdate, request: Request):
    """Update bucket attributes and optionally replace readonly account mappings.

    bucket_name is immutable and is not accepted here.
    """
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    account_ids = data.pop("account_ids", None)
    row = await run_in_threadpool(bucket_repo.update, bucket_id, data, user, account_ids)
    if row is None:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return row


@router.delete("/deleteBucket/{bucket_id}")
async def delete_bucket(bucket_id: str, background_tasks: BackgroundTasks):
    """Soft-delete a bucket (status → DELETED) and async-drop its Milvus collection.

    The Postgres soft-delete always succeeds before the Milvus task runs.
    Milvus drop failure is logged but does not affect the HTTP response.
    """
    details = await run_in_threadpool(
        bucket_detail_repo.get_by_bucket,
        bucket_id,
        True,
        None,
        None,
    )
    row = await run_in_threadpool(bucket_repo.delete, bucket_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bucket not found")
    background_tasks.add_task(_delete_milvus_collection, str(row["id"]), row["bucket_name"])
    detail_ids = [str(detail["id"]) for detail in details if detail.get("id")]
    if detail_ids:
        background_tasks.add_task(_delete_bucket_minio_assets, str(row["id"]), detail_ids)
    return row


@router.post("/provisionCallback")
async def provision_callback(payload: ProvisionCallback):
    """Called by external tools (or manually) to correct provision status."""
    row = await run_in_threadpool(
        bucket_repo.set_provision_result, payload.bucket_id, payload.status, payload.error_detail
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return row
