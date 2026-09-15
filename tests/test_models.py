"""Unit tests for Pydantic request models — validates field validators fire correctly."""

import pytest
from pydantic import ValidationError

from src.models.bucket import BucketCreate, BucketUpdate, ProvisionCallback
from src.models.bucket_detail import BucketDetailUpdate, IngestionCallback
from src.models.data_sql import DatabaseCreate, DatabaseUpdate, SqlQueryCreate, SqlQueryUpdate
from src.models.question import QuestionCreate, QuestionUpdate


# ---------------------------------------------------------------------------
# BucketCreate
# ---------------------------------------------------------------------------

class TestBucketCreate:
    def test_valid(self):
        m = BucketCreate(account_id="ACC1", bucket_name="ops_runbooks")
        assert m.bucket_name == "ops_runbooks"

    def test_invalid_name_hyphen(self):
        with pytest.raises(ValidationError):
            BucketCreate(account_id="ACC1", bucket_name="my-bucket")

    def test_invalid_name_starts_with_digit(self):
        with pytest.raises(ValidationError):
            BucketCreate(account_id="ACC1", bucket_name="2bad")

    def test_invalid_name_empty(self):
        with pytest.raises(ValidationError):
            BucketCreate(account_id="ACC1", bucket_name="")


# ---------------------------------------------------------------------------
# BucketUpdate
# ---------------------------------------------------------------------------

class TestBucketUpdate:
    def test_valid_status_active(self):
        assert BucketUpdate(status="ACTIVE").status == "ACTIVE"

    def test_valid_status_inactive(self):
        assert BucketUpdate(status="INACTIVE").status == "INACTIVE"

    def test_invalid_status_draft(self):
        with pytest.raises(ValidationError):
            BucketUpdate(status="DRAFT")

    def test_no_fields_is_valid(self):
        m = BucketUpdate()
        assert m.status is None
        assert m.account_ids is None

    def test_account_ids_accepted(self):
        m = BucketUpdate(account_ids=["ACC1", "ACC2"])
        assert len(m.account_ids) == 2


# ---------------------------------------------------------------------------
# ProvisionCallback
# ---------------------------------------------------------------------------

class TestProvisionCallback:
    def test_active(self):
        m = ProvisionCallback(bucket_id="abc", status="ACTIVE")
        assert m.error_detail is None

    def test_failed_with_detail(self):
        m = ProvisionCallback(bucket_id="abc", status="FAILED", error_detail="timeout")
        assert m.error_detail == "timeout"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            ProvisionCallback(bucket_id="abc", status="READY")


# ---------------------------------------------------------------------------
# BucketDetailUpdate
# ---------------------------------------------------------------------------

class TestBucketDetailUpdate:
    def test_valid_deleted(self):
        assert BucketDetailUpdate(status="DELETED").status == "DELETED"

    def test_valid_ingested(self):
        assert BucketDetailUpdate(status="INGESTED").status == "INGESTED"

    def test_invalid_status_active(self):
        with pytest.raises(ValidationError):
            BucketDetailUpdate(status="ACTIVE")

    def test_reingest_default_false(self):
        assert BucketDetailUpdate().reingest is False


# ---------------------------------------------------------------------------
# IngestionCallback
# ---------------------------------------------------------------------------

class TestIngestionCallback:
    def test_valid_ingested(self):
        m = IngestionCallback(id="abc", status="INGESTED", milvus_chunks_stored=10)
        assert m.milvus_chunks_stored == 10

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            IngestionCallback(id="abc", status="COMPLETE")

    def test_partial_payload_allowed(self):
        m = IngestionCallback(id="abc", status="FAILED", error_detail="disk full")
        assert m.milvus_source_id is None


# ---------------------------------------------------------------------------
# QuestionCreate / QuestionUpdate
# ---------------------------------------------------------------------------

class TestQuestionCreate:
    def test_valid_full(self):
        m = QuestionCreate(bucket_id="b1", question="Q?", answer="A", rank=3, match_threshold=0.85)
        assert m.rank == 3
        assert m.match_threshold == 0.85

    def test_rank_too_high(self):
        with pytest.raises(ValidationError):
            QuestionCreate(bucket_id="b1", question="Q?", answer="A", rank=6)

    def test_rank_too_low(self):
        with pytest.raises(ValidationError):
            QuestionCreate(bucket_id="b1", question="Q?", answer="A", rank=0)

    def test_rank_boundary_1(self):
        assert QuestionCreate(bucket_id="b1", question="Q?", answer="A", rank=1).rank == 1

    def test_rank_boundary_5(self):
        assert QuestionCreate(bucket_id="b1", question="Q?", answer="A", rank=5).rank == 5

    def test_match_threshold_out_of_range(self):
        with pytest.raises(ValidationError):
            QuestionCreate(bucket_id="b1", question="Q?", answer="A", match_threshold=1.5)

    def test_match_threshold_boundary_0(self):
        assert QuestionCreate(bucket_id="b1", question="Q?", answer="A", match_threshold=0.0).match_threshold == 0.0

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            QuestionCreate(bucket_id="b1", question="Q?", answer="A", status="ACTIVE")

    def test_valid_status_draft(self):
        assert QuestionCreate(bucket_id="b1", question="Q?", answer="A", status="DRAFT").status == "DRAFT"


class TestQuestionUpdate:
    def test_no_fields_valid(self):
        assert QuestionUpdate().rank is None

    def test_rank_out_of_range(self):
        with pytest.raises(ValidationError):
            QuestionUpdate(rank=10)


# ---------------------------------------------------------------------------
# DatabaseCreate / DatabaseUpdate
# ---------------------------------------------------------------------------

class TestDatabaseCreate:
    def test_valid_active(self):
        m = DatabaseCreate(bucket_id="b1", database_name="mydb", status="ACTIVE")
        assert m.status == "ACTIVE"

    def test_valid_inactive(self):
        assert DatabaseCreate(bucket_id="b1", database_name="mydb", status="INACTIVE").status == "INACTIVE"

    def test_invalid_status_provisioning(self):
        with pytest.raises(ValidationError):
            DatabaseCreate(bucket_id="b1", database_name="mydb", status="PROVISIONING")

    def test_invalid_status_draft(self):
        with pytest.raises(ValidationError):
            DatabaseCreate(bucket_id="b1", database_name="mydb", status="DRAFT")

    def test_invalid_status_pending(self):
        with pytest.raises(ValidationError):
            DatabaseCreate(bucket_id="b1", database_name="mydb", status="PENDING")

    def test_inline_credentials_rejected(self):
        with pytest.raises(ValidationError):
            DatabaseCreate(
                bucket_id="b1",
                database_name="mydb",
                connection_url="postgresql://user:secret@host:5432/db",
            )

    def test_credential_free_url_accepted(self):
        m = DatabaseCreate(
            bucket_id="b1",
            database_name="mydb",
            connection_url="postgresql://host:5432/db",
        )
        assert m.connection_url == "postgresql://host:5432/db"

    def test_no_status_is_valid(self):
        m = DatabaseCreate(bucket_id="b1", database_name="mydb")
        assert m.status is None


class TestDatabaseUpdate:
    def test_valid_archived(self):
        assert DatabaseUpdate(status="ARCHIVED").status == "ARCHIVED"

    def test_invalid_status_failed(self):
        with pytest.raises(ValidationError):
            DatabaseUpdate(status="FAILED")

    def test_inline_credentials_rejected(self):
        with pytest.raises(ValidationError):
            DatabaseUpdate(connection_url="postgresql://user:pass@host/db")


# ---------------------------------------------------------------------------
# SqlQueryCreate / SqlQueryUpdate
# ---------------------------------------------------------------------------

class TestSqlQueryCreate:
    def test_valid_full(self):
        m = SqlQueryCreate(database_id="d1", query_name="Q1", rank=2, quality_score=0.9, status="DRAFT")
        assert m.quality_score == 0.9

    def test_quality_score_out_of_range(self):
        with pytest.raises(ValidationError):
            SqlQueryCreate(database_id="d1", query_name="Q1", quality_score=1.5)

    def test_quality_score_boundary_1(self):
        assert SqlQueryCreate(database_id="d1", query_name="Q1", quality_score=1.0).quality_score == 1.0

    def test_status_published_accepted(self):
        assert SqlQueryCreate(database_id="d1", query_name="Q1", status="PUBLISHED").status == "PUBLISHED"

    def test_status_active_rejected(self):
        # SQL queries use CURATION_STATUSES (DRAFT/PUBLISHED/ARCHIVED), not ACTIVE
        with pytest.raises(ValidationError):
            SqlQueryCreate(database_id="d1", query_name="Q1", status="ACTIVE")


class TestSqlQueryUpdate:
    def test_no_fields_valid(self):
        assert SqlQueryUpdate().rank is None

    def test_rank_out_of_range(self):
        with pytest.raises(ValidationError):
            SqlQueryUpdate(rank=6)

    def test_quality_score_negative(self):
        with pytest.raises(ValidationError):
            SqlQueryUpdate(quality_score=-0.1)
