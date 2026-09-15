"""manageBucketDetails router (NEW). Table: nnp_bucket_details."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from src.api.deps import current_user
from src.models.bucket_detail import BucketDetailUpdate, GitBucketDetailCreate, IngestionCallback, RedmineBucketDetailCreate
from src.repositories import bucket_detail_repo, bucket_repo
from src.services import doc_reader, ingestion_pipeline, git_reader_tree_sitter, minio_storage, redmine_loader
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/manageBucketDetails", tags=["manageBucketDetails"])


async def _ingest_document_task(
    detail_id: str,
    bucket_name: str,
    doc_type: str,
    doc_name: str,
    content: str,
    use_local_embeddings: bool = False,
) -> None:
    """Background task: chunk → embed → store, then update the DB row."""
    ok, err, chunks = await ingestion_pipeline.ingest_document(
        detail_id, bucket_name, doc_type, doc_name, content,
        use_local_embeddings=use_local_embeddings,
    )
    if ok:
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "INGESTED",
                "milvus_source_id": f"km_{detail_id}",
                "milvus_chunks_stored": chunks,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": datetime.utcnow().isoformat(),
                "error_detail": None,
            },
        )
    else:
        logger.error("[_ingest_document_task] detail=%s failed: %s", detail_id, err)
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "FAILED",
                "milvus_source_id": None,
                "milvus_chunks_stored": None,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": None,
                "error_detail": err,
            },
        )


async def _delete_vectors_task(detail_id: str, bucket_name: str) -> None:
    """Background task: remove all vectors for this detail from Milvus."""
    try:
        ok, err = await ingestion_pipeline.delete_document(f"km_{detail_id}", bucket_name)
        if ok:
            logger.info("[_delete_vectors_task] success detail=%s", detail_id)
        else:
            logger.error("[_delete_vectors_task] failed detail=%s: %s", detail_id, err)
    except Exception as exc:  # noqa: BLE001
        logger.error("[_delete_vectors_task] detail=%s: %s", detail_id, exc)


async def _delete_minio_assets_task(detail_id: str) -> None:
    """Background task: remove MinIO visual artifacts for this detail."""
    try:
        ok = await run_in_threadpool(minio_storage.delete_document_assets, detail_id)
        if ok:
            logger.info("[_delete_minio_assets_task] success detail=%s", detail_id)
        else:
            logger.error("[_delete_minio_assets_task] failed detail=%s", detail_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[_delete_minio_assets_task] detail=%s: %s", detail_id, exc)


async def _mark_failed_task(
    detail_id: str,
    error_msg: str,
) -> None:
    try:
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "FAILED",
                "milvus_source_id": None,
                "milvus_chunks_stored": None,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": None,
                "error_detail": error_msg,
            },
        )
        logger.info("[_mark_failed_task] marked %s as FAILED", detail_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[_mark_failed_task] failed: %s", exc)


def _extract_uploaded_file_content(
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
) -> str:
    """Extract uploaded file content; PDFs use parser-first scanned-page support."""
    mime = (content_type or "").lower().split(";", 1)[0].strip()
    lower_filename = filename.lower()
    if mime == "application/pdf" or lower_filename.endswith(".pdf"):
        return doc_reader.read_pdf_with_scanned_page_support(file_bytes, filename)
    return doc_reader.read_file(file_bytes, filename, content_type)


def _is_pdf_file(filename: str, content_type: str | None) -> bool:
    mime = (content_type or "").lower().split(";", 1)[0].strip()
    return mime == "application/pdf" or filename.lower().endswith(".pdf")


async def _extract_and_ingest_file_task(
    detail_id: str,
    bucket_name: str,
    doc_type: str,
    doc_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
    use_local_embeddings: bool = False,
) -> None:
    """Background task: extract uploaded file content, then chunk/embed/store."""
    if _is_pdf_file(filename, content_type):
        try:
            documents = await run_in_threadpool(
                doc_reader.read_pdf_page_documents_with_visual_assets,
                file_bytes,
                filename,
                detail_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[_extract_and_ingest_file_task] detail=%s PDF extraction failed: %s", detail_id, exc)
            await _mark_failed_task(detail_id, str(exc))
            return

        if not documents:
            await _mark_failed_task(
                detail_id,
                "File content could not be extracted. Check file format and content.",
            )
            return

        ok, err, chunks = await ingestion_pipeline.ingest_document_parts(
            detail_id,
            bucket_name,
            doc_type,
            doc_name,
            documents,
            use_local_embeddings=use_local_embeddings,
        )
        if ok:
            await run_in_threadpool(
                bucket_detail_repo.apply_ingestion_result,
                {
                    "id": detail_id,
                    "status": "INGESTED",
                    "milvus_source_id": f"km_{detail_id}",
                    "milvus_chunks_stored": chunks,
                    "milvus_chunks_duplicated": None,
                    "ingest_request_id": None,
                    "ingested_at": datetime.utcnow().isoformat(),
                    "error_detail": None,
                },
            )
        else:
            logger.error("[_extract_and_ingest_file_task] detail=%s failed: %s", detail_id, err)
            await _mark_failed_task(detail_id, err or "PDF ingestion failed")
        return

    try:
        content = await run_in_threadpool(
            _extract_uploaded_file_content,
            file_bytes,
            filename,
            content_type,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[_extract_and_ingest_file_task] detail=%s extraction failed: %s", detail_id, exc)
        await _mark_failed_task(detail_id, str(exc))
        return

    if not content:
        await _mark_failed_task(
            detail_id,
            "File content could not be extracted. Check file format and content.",
        )
        return

    await _ingest_document_task(
        detail_id,
        bucket_name,
        doc_type,
        doc_name,
        content,
        use_local_embeddings=use_local_embeddings,
    )


async def _ingest_git_repository_task(
    detail_id: str,
    bucket_name: str,
    repo_url: str,
    branch: str | None,
    file_extensions: list[str] | None,
    username: str | None,
    token: str | None,
    use_local_embeddings: bool = False,
) -> None:
    """Background task: clone repo -> extract code units -> chunk/embed/store."""
    try:
        logger.info("[git-ingest] detail=%s cloning and extracting repository", detail_id)
        documents, files_processed = await run_in_threadpool(
            git_reader_tree_sitter.load_repository_documents,
            repo_url,
            branch,
            file_extensions,
            username,
            token,
        )
    except Exception as exc:  # noqa: BLE001
        safe_error = str(exc)
        if token:
            safe_error = safe_error.replace(token, "***")
        logger.error("❌ [git-ingest] detail=%s repository extraction failed: %s", detail_id, safe_error)
        await _mark_failed_task(detail_id, safe_error)
        return

    logger.info( "[git-ingest] detail=%s extracted files=%d documents=%d", detail_id, files_processed, len(documents))
    ok, err, chunks = await ingestion_pipeline.ingest_git_repository_documents(
        detail_id,
        bucket_name,
        repo_url,
        documents,
        use_local_embeddings=use_local_embeddings,
    )
    if ok:
        logger.info("[git-ingest] detail=%s updating DB status to INGESTED", detail_id)
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "INGESTED",
                "milvus_source_id": f"km_{detail_id}",
                "milvus_chunks_stored": chunks,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": datetime.utcnow().isoformat(),
                "error_detail": None,
            },
        )
    else:
        logger.info("📝 [git-ingest] detail=%s updating DB status to FAILED", detail_id)
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "FAILED",
                "milvus_source_id": None,
                "milvus_chunks_stored": None,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": None,
                "error_detail": err,
            },
        )


async def _ingest_redmine_issues_task(
    detail_id: str,
    bucket_name: str,
    redmine_url: str,
    api_key: str,
    project_id: str | None,
    status_id: str | None,
    limit: int | None,
    use_local_embeddings: bool = False,
) -> None:
    """Background task: fetch Redmine issues -> chunk/embed/store."""
    try:
        if not redmine_url or not api_key:
            await _mark_failed_task(
                detail_id,
                "Redmine URL and API key are required.",
            )
            return

        loader = redmine_loader.RedmineLoader(redmine_url, api_key)
        documents = await run_in_threadpool(
            loader.load_issues,
            project_id,
            status_id,
            limit,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[redmine-ingest] detail=%s issue extraction failed: %s", detail_id, exc)
        await _mark_failed_task(detail_id, str(exc))
        return

    logger.info("[redmine-ingest] detail=%s extracted issues=%d", detail_id, len(documents))
    ok, err, chunks = await ingestion_pipeline.ingest_redmine_issue_documents(
        detail_id,
        bucket_name,
        f"redmine:{project_id or 'all'}",
        documents,
        use_local_embeddings=use_local_embeddings,
    )
    if ok:
        logger.info("[redmine-ingest] detail=%s updating DB status to INGESTED", detail_id)
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "INGESTED",
                "milvus_source_id": f"km_{detail_id}",
                "milvus_chunks_stored": chunks,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": datetime.utcnow().isoformat(),
                "error_detail": None,
            },
        )
    else:
        logger.info("[redmine-ingest] detail=%s updating DB status to FAILED", detail_id)
        await run_in_threadpool(
            bucket_detail_repo.apply_ingestion_result,
            {
                "id": detail_id,
                "status": "FAILED",
                "milvus_source_id": None,
                "milvus_chunks_stored": None,
                "milvus_chunks_duplicated": None,
                "ingest_request_id": None,
                "ingested_at": None,
                "error_detail": err,
            },
        )


@router.get("/getDetails/{bucket_id}")
async def get_details(
    bucket_id: str,
    includeDeleted: bool = False,
    category: str | None = None,
    status: str | None = None,
):
    """Return all document rows in a bucket (optional category/status filters)."""
    return await run_in_threadpool(
        bucket_detail_repo.get_by_bucket, bucket_id, includeDeleted, category, status
    )


@router.post("/createBucketDetails", status_code=status.HTTP_202_ACCEPTED)
async def create_bucket_details(
    background_tasks: BackgroundTasks,
    request: Request,
    bucket_id: str = Form(...),
    doc_category: str = Form("document"),
    doc_name: str = Form(""),
    url: str = Form(""),
    file: UploadFile = File(None),
):
    """Register a document (status PENDING) and async-ingest it.

    Accepts multipart/form-data. Provide either a file upload or a URL;
    if neither is supplied the row is created as PENDING and no ingestion runs.
    """
    user = current_user(request)

    # Resolve source metadata. File extraction is intentionally deferred to the
    # background task so scanned PDF VLM calls do not delay the 202 response.
    content = ""
    file_bytes = b""
    file_content_type = None
    if file and file.filename:
        file_bytes = await file.read()
        file_content_type = file.content_type
        doc_name = doc_name or file.filename
    elif url:
        content = doc_reader.read_url(url)
        doc_name = doc_name or url

    # Verify the bucket exists and retrieve its Milvus collection name
    bucket = await run_in_threadpool(bucket_repo.get_by_id, bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Insert DB row as PENDING
    detail = await run_in_threadpool(
        bucket_detail_repo.create,
        {
            "bucket_id": bucket_id,
            "doc_category": doc_category,
            "doc_name": doc_name,
        },
        user,
    )

    if file and file.filename:
        background_tasks.add_task(
            _extract_and_ingest_file_task,
            str(detail["id"]),
            bucket["bucket_name"],
            doc_category,
            doc_name,
            file_bytes,
            file.filename,
            file_content_type,
            use_local_embeddings=(bucket.get("embedding_backend") == "local"),
        )
    elif content:
        background_tasks.add_task(
            _ingest_document_task,
            str(detail["id"]),
            bucket["bucket_name"],
            doc_category,
            doc_name,
            content,
            use_local_embeddings=(bucket.get("embedding_backend") == "local"),
        )
    elif url:
        # URL was provided but content extraction failed
        background_tasks.add_task(
            _mark_failed_task,
            str(detail["id"]),
            "No content extracted from URL. "
            "The page may require JavaScript "
            "rendering or blocked automated access.",
        )

    return detail


@router.post("/createGitBucketDetails", status_code=status.HTTP_202_ACCEPTED)
async def create_git_bucket_details(
    payload: GitBucketDetailCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Register a Git repository and async-ingest its supported files."""
    user = current_user(request)

    bucket = await run_in_threadpool(bucket_repo.get_by_id, payload.bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    logger.info( "[git-ingest] bucket resolved id=%s name=%s embedding_backend=%s", payload.bucket_id, bucket.get("bucket_name"), bucket.get("embedding_backend"))

    detail = await run_in_threadpool(
        bucket_detail_repo.create,
        {
            "bucket_id": payload.bucket_id,
            "doc_category": "git",
            "doc_name": payload.repo_url,
            "description": f"branch={payload.branch or 'default'}",
            "format": "git",
        },
        user,
    )

    background_tasks.add_task(
        _ingest_git_repository_task,
        str(detail["id"]),
        bucket["bucket_name"],
        payload.repo_url,
        payload.branch,
        payload.file_extensions,
        payload.username,
        payload.token,
        use_local_embeddings=(bucket.get("embedding_backend") == "local"),
    )

    return detail


@router.post("/createRedmineBucketDetails", status_code=status.HTTP_202_ACCEPTED)
async def create_redmine_bucket_details(
    payload: RedmineBucketDetailCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Register a Redmine issue source and async-ingest matching issues."""
    user = current_user(request)

    bucket = await run_in_threadpool(bucket_repo.get_by_id, payload.bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    redmine_url = payload.redmine_url
    api_key = payload.api_key
    if not redmine_url or not api_key:
        raise HTTPException(
            status_code=400,
            detail="redmine_url and api_key are required in payload.",
        )

    detail = await run_in_threadpool(
        bucket_detail_repo.create,
        {
            "bucket_id": payload.bucket_id,
            "doc_category": "redmine",
            "doc_name": f"redmine:{payload.project_id or 'all'}",
            "description": f"url={redmine_url}, status={payload.status or 'all'}, limit={payload.limit or 'all'}",
            "format": "redmine",
        },
        user,
    )

    background_tasks.add_task(
        _ingest_redmine_issues_task,
        str(detail["id"]),
        bucket["bucket_name"],
        redmine_url,
        api_key,
        payload.project_id,
        payload.status,
        payload.limit,
        use_local_embeddings=(bucket.get("embedding_backend") == "local"),
    )

    return detail


@router.put("/updateBucketDetails/{detail_id}")
async def update_bucket_details(
    detail_id: str, payload: BucketDetailUpdate, request: Request, background_tasks: BackgroundTasks
):
    """Update a document row; supports re-ingest (vector update) and soft-delete."""
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    reingest = data.pop("reingest", False)
    row = await run_in_threadpool(bucket_detail_repo.update, detail_id, data, user)
    if row is None:
        raise HTTPException(status_code=404, detail="Bucket detail not found")

    if data.get("status") == "DELETED" and row.get("milvus_source_id"):
        bucket = await run_in_threadpool(bucket_repo.get_by_id, row["bucket_id"])
        if bucket:
            background_tasks.add_task(
                _delete_vectors_task, str(row["id"]), bucket["bucket_name"]
            )
    elif reingest:
        # Re-ingestion is not yet wired to the direct pipeline — kept as a stub.
        logger.info("[updateBucketDetails] reingest requested for detail=%s (not yet implemented)", detail_id)

    return row


@router.delete("/deleteBucketDetail/{detail_id}")
async def delete_bucket_detail(detail_id: str, background_tasks: BackgroundTasks):
    """Soft-delete a document (status → DELETED) and async-remove its Milvus vectors."""
    row = await run_in_threadpool(bucket_detail_repo.delete, detail_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Bucket detail not found")
    if row.get("milvus_source_id"):
        bucket = await run_in_threadpool(bucket_repo.get_by_id, row["bucket_id"])
        if bucket:
            background_tasks.add_task(
                _delete_vectors_task, str(row["id"]), bucket["bucket_name"]
            )
    background_tasks.add_task(_delete_minio_assets_task, str(row["id"]))
    return row


@router.post("/ingestionCallback")
async def ingestion_callback(payload: IngestionCallback):
    """Called by external tools (or manually) to correct ingestion status."""
    row = await run_in_threadpool(bucket_detail_repo.apply_ingestion_result, payload.model_dump())
    if row is None:
        raise HTTPException(status_code=404, detail="Bucket detail not found")
    return row
