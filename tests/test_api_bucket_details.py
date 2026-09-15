"""API-layer tests for /manageBucketDetails."""

from unittest.mock import AsyncMock, patch

_BUCKET = {
    "id": "11111111-1111-1111-1111-111111111111",
    "bucket_name": "ops_runbooks",
}

_DETAIL = {
    "id": "22222222-2222-2222-2222-222222222222",
    "bucket_id": "11111111-1111-1111-1111-111111111111",
    "doc_name": "runbook.pdf",
    "doc_category": "document",
    "status": "PENDING",
    "milvus_source_id": None,
    "created_by": "test-user",
    "updated_by": "test-user",
}


# ---------------------------------------------------------------------------
# GET /manageBucketDetails/getDetails/{bucket_id}
# ---------------------------------------------------------------------------

def test_get_details_returns_list(client):
    with patch("src.repositories.bucket_detail_repo.get_by_bucket", return_value=[_DETAIL]):
        resp = client.get(f"/manageBucketDetails/getDetails/{_DETAIL['bucket_id']}")
    assert resp.status_code == 200
    assert resp.json()[0]["doc_name"] == "runbook.pdf"


def test_get_details_category_filter_passed(client):
    with patch("src.repositories.bucket_detail_repo.get_by_bucket", return_value=[]) as mock_fn:
        client.get(f"/manageBucketDetails/getDetails/{_DETAIL['bucket_id']}?category=web")
    _, _, cat, _ = mock_fn.call_args.args
    assert cat == "web"


# ---------------------------------------------------------------------------
# POST /manageBucketDetails/createBucketDetails (multipart/form-data)
# ---------------------------------------------------------------------------

def test_create_detail_202(client):
    with patch("src.repositories.bucket_repo.get_by_id", return_value=_BUCKET), \
         patch("src.repositories.bucket_detail_repo.create", return_value=_DETAIL):
        resp = client.post(
            "/manageBucketDetails/createBucketDetails",
            data={"bucket_id": _DETAIL["bucket_id"], "doc_name": "runbook.pdf"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 202
    assert resp.json()["status"] == "PENDING"


def test_create_detail_missing_bucket_id_422(client):
    resp = client.post(
        "/manageBucketDetails/createBucketDetails",
        data={"doc_name": "file.pdf"},
    )
    assert resp.status_code == 422


def test_create_detail_bucket_not_found_404(client):
    with patch("src.repositories.bucket_repo.get_by_id", return_value=None):
        resp = client.post(
            "/manageBucketDetails/createBucketDetails",
            data={"bucket_id": "nonexistent"},
        )
    assert resp.status_code == 404


def test_create_detail_no_content_skips_ingestion(client):
    """No file and no URL → row created, background ingestion NOT launched."""
    with patch("src.repositories.bucket_repo.get_by_id", return_value=_BUCKET), \
         patch("src.repositories.bucket_detail_repo.create", return_value=_DETAIL), \
         patch("src.services.ingestion_pipeline.ingest_document", new_callable=AsyncMock) as mock_ingest:
        resp = client.post(
            "/manageBucketDetails/createBucketDetails",
            data={"bucket_id": _DETAIL["bucket_id"]},
        )
    assert resp.status_code == 202
    mock_ingest.assert_not_called()


# ---------------------------------------------------------------------------
# PUT /manageBucketDetails/updateBucketDetails/{id}
# ---------------------------------------------------------------------------

def test_update_detail_200(client):
    updated = {**_DETAIL, "status": "INGESTED"}
    with patch("src.repositories.bucket_detail_repo.update", return_value=updated):
        resp = client.put(
            f"/manageBucketDetails/updateBucketDetails/{_DETAIL['id']}",
            json={"status": "INGESTED"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INGESTED"


def test_update_detail_404_when_not_found(client):
    with patch("src.repositories.bucket_detail_repo.update", return_value=None):
        resp = client.put(
            "/manageBucketDetails/updateBucketDetails/missing",
            json={"status": "INGESTED"},
        )
    assert resp.status_code == 404


def test_update_detail_invalid_status_422(client):
    resp = client.put(
        f"/manageBucketDetails/updateBucketDetails/{_DETAIL['id']}",
        json={"status": "ACTIVE"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /manageBucketDetails/ingestionCallback
# ---------------------------------------------------------------------------

def test_ingestion_callback_200(client):
    ingested = {**_DETAIL, "status": "INGESTED", "milvus_chunks_stored": 47}
    with patch("src.repositories.bucket_detail_repo.apply_ingestion_result", return_value=ingested):
        resp = client.post(
            "/manageBucketDetails/ingestionCallback",
            json={"id": _DETAIL["id"], "status": "INGESTED", "milvus_chunks_stored": 47},
        )
    assert resp.status_code == 200
    assert resp.json()["milvus_chunks_stored"] == 47


def test_ingestion_callback_invalid_status_422(client):
    resp = client.post(
        "/manageBucketDetails/ingestionCallback",
        json={"id": _DETAIL["id"], "status": "DONE"},
    )
    assert resp.status_code == 422


def test_ingestion_callback_404_when_not_found(client):
    with patch("src.repositories.bucket_detail_repo.apply_ingestion_result", return_value=None):
        resp = client.post(
            "/manageBucketDetails/ingestionCallback",
            json={"id": "missing", "status": "INGESTED"},
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /manageBucketDetails/deleteBucketDetail/{id}
# ---------------------------------------------------------------------------

def test_delete_bucket_detail_200(client):
    deleted = {**_DETAIL, "status": "DELETED"}
    with patch("src.repositories.bucket_detail_repo.delete", return_value=deleted):
        resp = client.delete(f"/manageBucketDetails/deleteBucketDetail/{_DETAIL['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


def test_delete_bucket_detail_404_when_not_found(client):
    with patch("src.repositories.bucket_detail_repo.delete", return_value=None):
        resp = client.delete("/manageBucketDetails/deleteBucketDetail/missing")
    assert resp.status_code == 404


def test_delete_bucket_detail_triggers_milvus_delete(client):
    deleted = {**_DETAIL, "status": "DELETED", "milvus_source_id": f"km_{_DETAIL['id']}"}
    with patch("src.repositories.bucket_detail_repo.delete", return_value=deleted), \
         patch("src.repositories.bucket_repo.get_by_id", return_value=_BUCKET), \
         patch("src.services.ingestion_pipeline.delete_document",
               new_callable=AsyncMock, return_value=(True, None)) as mock_del:
        resp = client.delete(f"/manageBucketDetails/deleteBucketDetail/{_DETAIL['id']}")
    assert resp.status_code == 200
    mock_del.assert_called_once_with(f"km_{_DETAIL['id']}", _BUCKET["bucket_name"])


def test_delete_bucket_detail_no_milvus_delete_when_no_source_id(client):
    deleted = {**_DETAIL, "status": "DELETED", "milvus_source_id": None}
    with patch("src.repositories.bucket_detail_repo.delete", return_value=deleted), \
         patch("src.services.ingestion_pipeline.delete_document",
               new_callable=AsyncMock) as mock_del:
        resp = client.delete(f"/manageBucketDetails/deleteBucketDetail/{_DETAIL['id']}")
    assert resp.status_code == 200
    mock_del.assert_not_called()
