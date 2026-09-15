"""Unit tests for src/utils/validators.py — pure functions, no DB needed."""

from src.utils.validators import (
    BUCKET_STATUSES,
    CURATION_STATUSES,
    DB_STATUSES,
    DOC_STATUSES,
    has_inline_credentials,
    is_valid_milvus_name,
)


class TestMilvusName:
    def test_simple_valid(self):
        assert is_valid_milvus_name("ops_runbooks") is True

    def test_starts_with_underscore(self):
        assert is_valid_milvus_name("_private") is True

    def test_starts_with_letter_has_digits(self):
        assert is_valid_milvus_name("bucket2") is True

    def test_exactly_255_chars(self):
        assert is_valid_milvus_name("a" * 255) is True

    def test_empty_string(self):
        assert is_valid_milvus_name("") is False

    def test_starts_with_digit(self):
        assert is_valid_milvus_name("2bad") is False

    def test_contains_hyphen(self):
        assert is_valid_milvus_name("my-bucket") is False

    def test_contains_space(self):
        assert is_valid_milvus_name("my bucket") is False

    def test_256_chars_too_long(self):
        assert is_valid_milvus_name("a" * 256) is False


class TestInlineCredentials:
    def test_clean_url_no_creds(self):
        assert has_inline_credentials("postgresql://host:5432/db") is False

    def test_with_user_and_password(self):
        assert has_inline_credentials("postgresql://user:pass@host:5432/db") is True

    def test_empty_string(self):
        assert has_inline_credentials("") is False

    def test_plain_http_no_creds(self):
        assert has_inline_credentials("http://myservice/api") is False

    def test_at_sign_without_password_not_flagged(self):
        # only user@host with no colon-password is NOT flagged
        assert has_inline_credentials("postgresql://user@host/db") is False


class TestStatusVocabularies:
    def test_bucket_statuses_contains_provisioning_and_failed(self):
        assert {"PROVISIONING", "ACTIVE", "INACTIVE", "ARCHIVED", "FAILED", "DELETED"} == BUCKET_STATUSES

    def test_doc_statuses(self):
        assert {"PENDING", "INGESTED", "FAILED", "DELETED"} == DOC_STATUSES

    def test_curation_statuses(self):
        assert {"DRAFT", "PUBLISHED", "ARCHIVED", "DELETED"} == CURATION_STATUSES

    def test_db_statuses_excludes_provisioning_and_draft(self):
        assert {"ACTIVE", "INACTIVE", "ARCHIVED", "DELETED"} == DB_STATUSES
        assert "PROVISIONING" not in DB_STATUSES
        assert "DRAFT" not in DB_STATUSES
