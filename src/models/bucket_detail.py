"""manageBucketDetails request models (NEW)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.utils.validators import DOC_STATUSES


class BucketDetailCreate(BaseModel):
    """Body for POST /manageBucketDetails/createBucketDetails."""

    bucket_id: str
    doc_category: Optional[str] = None
    doc_name: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    doc_size: Optional[int] = None


class GitBucketDetailCreate(BaseModel):
    """Body for POST /manageBucketDetails/createGitBucketDetails."""

    bucket_id: str
    repo_url: str
    branch: Optional[str] = None
    file_extensions: Optional[List[str]] = None
    username: Optional[str] = None
    token: Optional[str] = None


class RedmineBucketDetailCreate(BaseModel):
    """Body for POST /manageBucketDetails/createRedmineBucketDetails."""

    bucket_id: str
    redmine_url: str
    api_key: str
    project_id: Optional[str] = None
    status: Optional[str] = None
    limit: Optional[int] = 100


class BucketDetailUpdate(BaseModel):
    """Body for PUT /manageBucketDetails/updateBucketDetails/{id}.

    Set status='DELETED' to soft-delete (triggers delete_by_source in Milvus).
    Set reingest=true to re-run ingestion and refresh the vectors.
    """

    doc_category: Optional[str] = None
    doc_name: Optional[str] = None
    description: Optional[str] = None
    format: Optional[str] = None
    doc_size: Optional[int] = None
    status: Optional[str] = None
    reingest: Optional[bool] = False

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in DOC_STATUSES:
            raise ValueError(f"status must be one of {sorted(DOC_STATUSES)}")
        return v


class IngestionCallback(BaseModel):
    """Body for POST /manageBucketDetails/ingestionCallback (called by the ingestion service)."""

    id: str
    status: str
    milvus_source_id: Optional[str] = None
    milvus_chunks_stored: Optional[int] = None
    milvus_chunks_duplicated: Optional[int] = None
    ingest_request_id: Optional[str] = None
    ingested_at: Optional[datetime] = None
    error_detail: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in DOC_STATUSES:
            raise ValueError(f"status must be one of {sorted(DOC_STATUSES)}")
        return v
