"""Validation helpers (NEW).

The CoreComp DB is intentionally permissive (no NOT NULL / CHECK / UNIQUE in
v1 — see db/schema.sql), so this service is the validation gatekeeper.
These helpers back the Pydantic field validators in src/models/*.
"""

import re

# Milvus collection naming rules — bucket_name doubles as the collection name.
MILVUS_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,254}$")

# Status vocabularies (documented as comments in the DB, enforced here).
BUCKET_STATUSES = {"PROVISIONING", "ACTIVE", "INACTIVE", "ARCHIVED", "FAILED", "DELETED"}
DOC_STATUSES = {"PENDING", "INGESTED", "FAILED", "DELETED"}
CURATION_STATUSES = {"DRAFT", "PUBLISHED", "ARCHIVED", "DELETED"}
DB_STATUSES = {"ACTIVE", "INACTIVE", "ARCHIVED", "DELETED"}

# Detects inline credentials in a connection URL, e.g. scheme://user:pass@host
_INLINE_CRED_RE = re.compile(r"://[^/@\s]*:[^/@\s]*@")


def is_valid_milvus_name(name: str) -> bool:
    return bool(name) and bool(MILVUS_NAME_RE.match(name))


def has_inline_credentials(url: str) -> bool:
    return bool(url) and bool(_INLINE_CRED_RE.search(url))
