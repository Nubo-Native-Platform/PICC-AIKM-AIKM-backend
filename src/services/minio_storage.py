"""MinIO storage helpers for Knowledge Base visual artifacts."""

from contextlib import closing
import io

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def upload_pdf_figure_image(
    image_bytes: bytes,
    detail_id: str,
    page_number: int,
    figure_index: int,
    caption: str | None = None,
    bbox: list[float] | None = None,
) -> dict | None:
    """Upload a cropped PDF figure image and return metadata for Milvus."""
    if not image_bytes:
        return None
    if not settings.minio_root_password:
        logger.warning("[upload_pdf_figure_image] MINIO_ROOT_PASSWORD is missing")
        return None

    try:
        from minio import Minio

        client = Minio(
            settings.minio_host,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        bucket = settings.minio_bucket
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        object_key = (
            f"km/{detail_id}/figures/"
            f"page_{page_number:04d}_figure_{figure_index:02d}.png"
        )
        client.put_object(
            bucket,
            object_key,
            io.BytesIO(image_bytes),
            length=len(image_bytes),
            content_type="image/png",
        )
        return {
            "asset_id": f"km_{detail_id}_page_{page_number}_figure_{figure_index}",
            "type": "figure",
            "label": f"Figure {figure_index} on page {page_number}",
            "caption": caption,
            "bucket": bucket,
            "object_key": object_key,
            "page_number": page_number,
            "figure_index": figure_index,
            "bbox": bbox,
            "mime_type": "image/png",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[upload_pdf_figure_image] failed detail=%s page=%s figure=%s: %s",
            detail_id,
            page_number,
            figure_index,
            exc,
        )
        return None


def delete_document_assets(detail_id: str) -> bool:
    """Delete all MinIO visual artifacts for one ingested document."""
    if not settings.minio_root_password:
        logger.warning("[delete_document_assets] MINIO_ROOT_PASSWORD is missing")
        return False

    try:
        from minio import Minio

        client = Minio(
            settings.minio_host,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        bucket = settings.minio_bucket
        if not client.bucket_exists(bucket):
            return True

        prefix = f"km/{detail_id}/"
        deleted = 0
        for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
            client.remove_object(bucket, obj.object_name)
            deleted += 1

        logger.info(
            "[delete_document_assets] detail=%s deleted_objects=%d",
            detail_id,
            deleted,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("[delete_document_assets] failed detail=%s: %s", detail_id, exc)
        return False


def delete_documents_assets(detail_ids: list[str]) -> int:
    """Delete MinIO visual artifacts for multiple ingested documents."""
    deleted_prefixes = 0
    for detail_id in detail_ids:
        if delete_document_assets(detail_id):
            deleted_prefixes += 1
    return deleted_prefixes


def get_image_asset(bucket: str, object_key: str):
    """Fetch a visual artifact from the configured MinIO bucket."""
    if not settings.minio_root_password:
        raise RuntimeError("MINIO_ROOT_PASSWORD is missing")
    if bucket != settings.minio_bucket:
        raise ValueError(f"Bucket is not allowed: {bucket}")

    from minio import Minio

    client = Minio(
        settings.minio_host,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    return client.get_object(bucket, object_key)


def iter_minio_object(response):
    with closing(response):
        for chunk in response.stream(32 * 1024):
            yield chunk
        response.release_conn()
