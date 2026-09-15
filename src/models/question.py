"""manageQuestions request models (NEW)."""

from typing import Optional

from pydantic import BaseModel, field_validator

from src.utils.validators import CURATION_STATUSES


def _check_rank(v: Optional[int]) -> Optional[int]:
    if v is not None and not (1 <= v <= 5):
        raise ValueError("rank must be between 1 and 5")
    return v


def _check_threshold(v: Optional[float]) -> Optional[float]:
    if v is not None and not (0.0 <= v <= 1.0):
        raise ValueError("match_threshold must be between 0 and 1")
    return v


def _check_status(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in CURATION_STATUSES:
        raise ValueError(f"status must be one of {sorted(CURATION_STATUSES)}")
    return v


class QuestionCreate(BaseModel):
    """Body for POST /manageQuestions/addQDetails. answer is plain text."""

    bucket_id: str
    question: str
    answer: str
    rank: Optional[int] = None
    status: Optional[str] = None
    match_threshold: Optional[float] = None

    _v_rank = field_validator("rank")(_check_rank)
    _v_threshold = field_validator("match_threshold")(_check_threshold)
    _v_status = field_validator("status")(_check_status)


class QuestionUpdate(BaseModel):
    """Body for PUT /manageQuestions/updateQDetails/{id}."""

    question: Optional[str] = None
    answer: Optional[str] = None
    rank: Optional[int] = None
    status: Optional[str] = None
    match_threshold: Optional[float] = None

    _v_rank = field_validator("rank")(_check_rank)
    _v_threshold = field_validator("match_threshold")(_check_threshold)
    _v_status = field_validator("status")(_check_status)
