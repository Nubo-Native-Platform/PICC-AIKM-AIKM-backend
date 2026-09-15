"""manageBucket request models (NEW)."""

from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.utils.validators import BUCKET_STATUSES, is_valid_milvus_name


class BucketCreate(BaseModel):
    """Body for POST /manageBucket/createBucket. Creates one bucket for one account."""

    account_id: str
    bucket_name: str
    bucket_category: Optional[str] = None
    bucket_desc: Optional[str] = None
    bucket_spec: Optional[str] = None
    bucket_url: Optional[str] = None

    @field_validator("bucket_name")
    @classmethod
    def _valid_bucket_name(cls, v: str) -> str:
        # bucket_name doubles as the Milvus collection name.
        if not is_valid_milvus_name(v):
            raise ValueError(
                "bucket_name must follow Milvus collection naming rules: only "
                "letters, digits and underscores; start with a letter or "
                "underscore; max 255 chars."
            )
        return v


class BucketUpdate(BaseModel):
    """Body for PUT /manageBucket/updateBucket/{id}.

    bucket_name is intentionally absent — it is immutable (it is the live Milvus
    collection name). If account_ids is supplied it replaces the bucket's
    readonly account mappings while preserving the owner mapping.
    """

    bucket_category: Optional[str] = None
    bucket_desc: Optional[str] = None
    bucket_spec: Optional[str] = None
    bucket_url: Optional[str] = None
    status: Optional[str] = None
    account_ids: Optional[List[str]] = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in BUCKET_STATUSES:
            raise ValueError(f"status must be one of {sorted(BUCKET_STATUSES)}")
        return v


class ProvisionCallback(BaseModel):
    """Body for POST /manageBucket/provisionCallback (called by the Milvus-provision service)."""

    bucket_id: str
    status: str
    error_detail: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in BUCKET_STATUSES:
            raise ValueError(f"status must be one of {sorted(BUCKET_STATUSES)}")
        return v
