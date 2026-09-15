"""manageDataSql request models (NEW) — databases + their saved queries."""

from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.utils.validators import CURATION_STATUSES, DB_STATUSES, has_inline_credentials


def _check_rank(v: Optional[int]) -> Optional[int]:
    if v is not None and not (1 <= v <= 5):
        raise ValueError("rank must be between 1 and 5")
    return v


def _check_quality(v: Optional[float]) -> Optional[float]:
    if v is not None and not (0.0 <= v <= 1.0):
        raise ValueError("quality_score must be between 0 and 1")
    return v


def _check_status(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in CURATION_STATUSES:
        raise ValueError(f"status must be one of {sorted(CURATION_STATUSES)}")
    return v


def _check_db_status(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in DB_STATUSES:
        raise ValueError(f"status must be one of {sorted(DB_STATUSES)}")
    return v


def _check_connection_url(v: Optional[str]) -> Optional[str]:
    # Credentials are supplied by the user at runtime, never stored.
    if v is not None and has_inline_credentials(v):
        raise ValueError(
            "connection_url must not contain inline credentials (user:pass@). "
            "Credentials are supplied at connection time."
        )
    return v


class DatabaseCreate(BaseModel):
    """Body for POST /manageDataSql/addDBDetails.

    connection_url must be credential-less (validated).
    connection_credential is an optional JSON string for dev/test use only —
    not validated for credential content.
    area is an optional domain/area label used for Vanna training context.
    """

    bucket_id: str
    database_name: str
    database_type: Optional[str] = None
    database_desc: Optional[str] = None
    connection_url: Optional[str] = None
    connection_credential: Optional[str] = None
    area: Optional[str] = None
    training_script: Optional[str] = None
    keywords: Optional[List[str]] = None
    status: Optional[str] = None

    _v_status = field_validator("status")(_check_db_status)
    _v_url = field_validator("connection_url")(_check_connection_url)


class DatabaseUpdate(BaseModel):
    """Body for PUT /manageDataSql/updateDBDetails/{id}.

    connection_url must be credential-less (validated).
    connection_credential is an optional JSON string for dev/test use only —
    not validated for credential content.
    area is an optional domain/area label used for Vanna training context.
    """

    database_name: Optional[str] = None
    database_type: Optional[str] = None
    database_desc: Optional[str] = None
    connection_url: Optional[str] = None
    connection_credential: Optional[str] = None
    area: Optional[str] = None
    training_script: Optional[str] = None
    keywords: Optional[List[str]] = None
    status: Optional[str] = None

    _v_status = field_validator("status")(_check_db_status)
    _v_url = field_validator("connection_url")(_check_connection_url)


class SqlQueryCreate(BaseModel):
    """Body for POST /manageDataSql/addSQLDetails. Parent key is database_id."""

    database_id: str
    query_name: str
    query_desc: Optional[str] = None
    query_context: Optional[str] = None
    query_text: Optional[str] = None
    status: Optional[str] = None
    rank: Optional[int] = None
    milvus_exemplar_id: Optional[str] = None
    quality_score: Optional[float] = None

    _v_rank = field_validator("rank")(_check_rank)
    _v_quality = field_validator("quality_score")(_check_quality)
    _v_status = field_validator("status")(_check_status)


class SqlQueryUpdate(BaseModel):
    """Body for PUT /manageDataSql/updateSQLDetails/{id}."""

    query_name: Optional[str] = None
    query_desc: Optional[str] = None
    query_context: Optional[str] = None
    query_text: Optional[str] = None
    status: Optional[str] = None
    rank: Optional[int] = None
    milvus_exemplar_id: Optional[str] = None
    quality_score: Optional[float] = None

    _v_rank = field_validator("rank")(_check_rank)
    _v_quality = field_validator("quality_score")(_check_quality)
    _v_status = field_validator("status")(_check_status)


class DDLCreate(BaseModel):
    """Body for POST /manageDataSql/addDDLDetails."""

    database_id: str
    table_name: Optional[str] = None
    ddl_text: str


class DDLUpdate(BaseModel):
    """Body for PUT /manageDataSql/updateDDLDetails/{id}."""

    table_name: Optional[str] = None
    ddl_text: Optional[str] = None


class RuleCreate(BaseModel):
    """Body for POST /manageDataSql/addRuleDetails."""

    database_id: str
    rule_name: Optional[str] = None
    rule_text: str


class RuleUpdate(BaseModel):
    """Body for PUT /manageDataSql/updateRuleDetails/{id}."""

    rule_name: Optional[str] = None
    rule_text: Optional[str] = None
