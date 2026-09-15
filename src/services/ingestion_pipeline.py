"""Ingestion pipeline: chunk → embed → store in Milvus (NEW).

Orchestrates the three steps for a single document and writes the result
back to Postgres via bucket_detail_repo. All public functions are async
and never raise — errors are returned as (False, message).
"""

from src.services import milvus_client
from src.services.embeddings import chunk_text, embed_texts, embed_texts_local
from src.services.git_ingestion_chunks import chunk_git_documents
from src.utils.logger import get_logger

logger = get_logger(__name__)

_MILVUS_CONTENT_MAX_CHARS = 4096


def _fit_milvus_content(content: str) -> list[str]:
    """Split content so every piece fits the Milvus content varchar limit."""
    if len(content.encode("utf-8")) <= _MILVUS_CONTENT_MAX_CHARS:
        return [content]

    pieces: list[str] = []
    current: list[str] = []
    current_bytes = 0
    for char in content:
        char_bytes = len(char.encode("utf-8"))
        if current and current_bytes + char_bytes > _MILVUS_CONTENT_MAX_CHARS:
            pieces.append("".join(current))
            current = []
            current_bytes = 0
        current.append(char)
        current_bytes += char_bytes
    if current:
        pieces.append("".join(current))
    return pieces


async def ingest_document(
    detail_id: str,
    bucket_name: str,
    doc_type: str,
    doc_name: str,
    content: str,
    use_local_embeddings: bool = False,
) -> tuple[bool, str | None, int]:
    """Chunk, embed and store a document in the bucket's Milvus collection.

    Returns (success, error_msg, chunks_stored). Never raises.
    """
    try:
        chunks = [
            fitted
            for chunk in chunk_text(content, doc_type)
            for fitted in _fit_milvus_content(chunk)
        ]
        if not chunks:
            return False, "No content extracted", 0

        if use_local_embeddings:
            embeddings = embed_texts_local(chunks)
        else:
            embeddings = embed_texts(chunks)
        if len(embeddings) != len(chunks):
            return False, "Embedding failed", 0

        source_id = f"km_{detail_id}"
        entities = [
            {
                "id": f"{source_id}_{i}",
                "embedding": embeddings[i],
                "content": chunks[i],
                "source": source_id,
                "doc_type": doc_type,
                "metadata": {
                    "detail_id": detail_id,
                    "doc_name": doc_name,
                    "chunk_index": i,
                },
            }
            for i in range(len(chunks))
        ]

        ok, err = await milvus_client.insert_vectors(bucket_name, entities)
        if not ok:
            return False, err, 0

        logger.info(
            "[ingest_document] success detail=%s bucket=%s chunks=%d",
            detail_id, bucket_name, len(chunks),
        )
        return True, None, len(chunks)
    except Exception as exc:  # noqa: BLE001
        logger.error("[ingest_document] detail=%s: %s", detail_id, exc)
        return False, str(exc), 0


async def ingest_document_parts(
    detail_id: str,
    bucket_name: str,
    doc_type: str,
    doc_name: str,
    documents: list[dict],
    use_local_embeddings: bool = False,
) -> tuple[bool, str | None, int]:
    """Chunk, embed, and store documents while preserving per-part metadata."""
    try:
        chunked_docs: list[dict] = []
        for document_index, document in enumerate(documents):
            content = (document.get("content") or "").strip()
            if not content:
                continue
            metadata = dict(document.get("metadata") or {})
            for local_chunk_index, chunk in enumerate(chunk_text(content, doc_type)):
                for split_chunk_index, fitted in enumerate(_fit_milvus_content(chunk)):
                    chunked_docs.append(
                        {
                            "content": fitted,
                            "metadata": {
                                **metadata,
                                "detail_id": detail_id,
                                "doc_name": metadata.get("doc_name") or doc_name,
                                "document_index": document_index,
                                "local_chunk_index": local_chunk_index,
                                "split_chunk_index": split_chunk_index,
                            },
                        }
                    )

        if not chunked_docs:
            return False, "No content extracted", 0

        chunks = [doc["content"] for doc in chunked_docs]
        if use_local_embeddings:
            embeddings = embed_texts_local(chunks)
        else:
            embeddings = embed_texts(chunks)
        if len(embeddings) != len(chunks):
            return False, "Embedding failed", 0

        source_id = f"km_{detail_id}"
        entities = []
        for i, doc in enumerate(chunked_docs):
            metadata = {**doc["metadata"], "chunk_index": i}
            entities.append(
                {
                    "id": f"{source_id}_{i}",
                    "embedding": embeddings[i],
                    "content": doc["content"],
                    "source": source_id,
                    "doc_type": doc_type,
                    "metadata": metadata,
                }
            )

        ok, err = await milvus_client.insert_vectors(bucket_name, entities)
        if not ok:
            return False, err, 0

        logger.info(
            "[ingest_document_parts] success detail=%s bucket=%s chunks=%d",
            detail_id,
            bucket_name,
            len(chunks),
        )
        return True, None, len(chunks)
    except Exception as exc:  # noqa: BLE001
        logger.error("[ingest_document_parts] detail=%s: %s", detail_id, exc)
        return False, str(exc), 0


async def ingest_git_repository_documents(
    detail_id: str,
    bucket_name: str,
    doc_name: str,
    documents: list[dict],
    use_local_embeddings: bool = False,
) -> tuple[bool, str | None, int]:
    """Chunk, embed, and store structured Git repository documents."""
    try:
        logger.info("[ingest_git_repository_documents] detail=%s started documents=%d bucket=%s", detail_id, len(documents), bucket_name)
        chunked_docs = chunk_git_documents(documents)
        if not chunked_docs:
            return False, "No content extracted", 0

        chunks = [doc["content"] for doc in chunked_docs]
        logger.info("[ingest_git_repository_documents] detail=%s embedding chunks=%d backend=%s", detail_id, len(chunks), "local" if use_local_embeddings else "openai")
        if use_local_embeddings:
            embeddings = embed_texts_local(chunks)
        else:
            embeddings = embed_texts(chunks)
        if len(embeddings) != len(chunks):
            return False, "Embedding failed", 0

        source_id = f"km_{detail_id}"
        entities = []
        for i, doc in enumerate(chunked_docs):
            metadata = {
                **doc["metadata"],
                "detail_id": detail_id,
                "doc_name": doc_name,
                "chunk_index": i,
            }
            entities.append({
                "id": f"{source_id}_{i}",
                "embedding": embeddings[i],
                "content": doc["content"],
                "source": source_id,
                "doc_type": metadata.get("type") or "git",
                "metadata": metadata,
            })

        logger.info( "[ingest_git_repository_documents] detail=%s inserting vectors bucket=%s entities=%d", detail_id, bucket_name, len(entities))
        ok, err = await milvus_client.insert_vectors(bucket_name, entities)
        if not ok:
            return False, err, 0

        logger.info( "[ingest_git_repository_documents] success detail=%s bucket=%s documents=%d chunks=%d", detail_id, bucket_name, len(documents), len(chunks))
        return True, None, len(chunks)
    except Exception as exc:  # noqa: BLE001
        logger.error("[ingest_git_repository_documents] detail=%s: %s", detail_id, exc)
        return False, str(exc), 0


async def ingest_redmine_issue_documents(
    detail_id: str,
    bucket_name: str,
    doc_name: str,
    documents: list[dict],
    use_local_embeddings: bool = False,
) -> tuple[bool, str | None, int]:
    """Chunk, embed, and store Redmine issue documents."""
    try:
        logger.info(
            "[ingest_redmine_issue_documents] detail=%s started documents=%d bucket=%s",
            detail_id, len(documents), bucket_name,
        )

        chunked_docs = []
        for doc_index, doc in enumerate(documents):
            metadata = dict(doc.get("metadata") or {})
            content = doc.get("content") or ""
            chunks = chunk_text(content, metadata.get("type") or "redmine")
            for chunk_index, chunk in enumerate(chunks):
                fitted_chunks = _fit_milvus_content(chunk)
                for split_chunk_index, fitted_chunk in enumerate(fitted_chunks):
                    chunked_docs.append({
                        "content": fitted_chunk,
                        "metadata": {
                            **metadata,
                            "detail_id": detail_id,
                            "doc_name": doc_name,
                            "document_index": doc_index,
                            "chunk_index": chunk_index,
                            "split_chunk_index": split_chunk_index,
                        },
                    })

        if not chunked_docs:
            return False, "No content extracted", 0

        chunks = [doc["content"] for doc in chunked_docs]
        logger.info(
            "[ingest_redmine_issue_documents] detail=%s embedding chunks=%d backend=%s",
            detail_id, len(chunks), "local" if use_local_embeddings else "openai",
        )
        if use_local_embeddings:
            embeddings = embed_texts_local(chunks)
        else:
            embeddings = embed_texts(chunks)
        if len(embeddings) != len(chunks):
            return False, "Embedding failed", 0

        source_id = f"km_{detail_id}"
        entities = []
        for i, doc in enumerate(chunked_docs):
            metadata = {**doc["metadata"], "chunk_index": i}
            entities.append({
                "id": f"{source_id}_{i}",
                "embedding": embeddings[i],
                "content": doc["content"],
                "source": source_id,
                "doc_type": metadata.get("type") or "redmine_issue",
                "metadata": metadata,
            })

        ok, err = await milvus_client.insert_vectors(bucket_name, entities)
        if not ok:
            return False, err, 0

        logger.info(
            "[ingest_redmine_issue_documents] success detail=%s bucket=%s documents=%d chunks=%d",
            detail_id, bucket_name, len(documents), len(chunks),
        )
        return True, None, len(chunks)
    except Exception as exc:  # noqa: BLE001
        logger.error("[ingest_redmine_issue_documents] detail=%s: %s", detail_id, exc)
        return False, str(exc), 0


async def delete_document(
    source_id: str,
    bucket_name: str,
) -> tuple[bool, str | None]:
    """Delete all vectors for a source_id from the bucket's Milvus collection.

    Returns (success, error_msg). Never raises.
    """
    try:
        ok, err = await milvus_client.delete_by_source(bucket_name, source_id)
        if ok:
            logger.info(
                "[delete_document] success source=%s bucket=%s", source_id, bucket_name
            )
        else:
            logger.error(
                "[delete_document] failed source=%s bucket=%s: %s",
                source_id, bucket_name, err,
            )
        return ok, err
    except Exception as exc:  # noqa: BLE001
        logger.error("[delete_document] source=%s bucket=%s: %s", source_id, bucket_name, exc)
        return False, str(exc)
