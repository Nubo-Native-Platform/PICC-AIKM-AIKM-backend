"""API-layer tests for /manageDataSql."""

from unittest.mock import AsyncMock, MagicMock, patch

_DB = {
    "id": "44444444-4444-4444-4444-444444444444",
    "bucket_id": "11111111-1111-1111-1111-111111111111",
    "database_name": "nnp_devsecops",
    "database_type": "postgres",
    "connection_url": "postgresql://host:5432/db",
    "status": "ACTIVE",
    "queries": [],
}

_QUERY = {
    "id": "55555555-5555-5555-5555-555555555555",
    "database_id": _DB["id"],
    "query_name": "Daily signups",
    "query_text": "SELECT count(*) FROM users WHERE created_at::date = CURRENT_DATE",
    "rank": 2,
    "status": "DRAFT",
    "quality_score": 1.0,
}


# ---------------------------------------------------------------------------
# GET /manageDataSql/getDetails
# ---------------------------------------------------------------------------

def test_get_details_returns_list(client):
    with patch("src.repositories.data_sql_repo.get_by_buckets", return_value=[_DB]):
        resp = client.get(f"/manageDataSql/getDetails?bucketIds={_DB['bucket_id']}")
    assert resp.status_code == 200
    assert resp.json()[0]["database_name"] == "nnp_devsecops"


def test_get_details_missing_bucket_ids_422(client):
    resp = client.get("/manageDataSql/getDetails")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /manageDataSql/addDBDetails
# ---------------------------------------------------------------------------

def test_add_db_details_201(client):
    with patch("src.repositories.data_sql_repo.create_database", return_value=_DB):
        resp = client.post(
            "/manageDataSql/addDBDetails",
            json={
                "bucket_id": _DB["bucket_id"],
                "database_name": "nnp_devsecops",
                "database_type": "postgres",
                "connection_url": "postgresql://host:5432/db",
                "status": "ACTIVE",
            },
            headers={"User": "test-user"},
        )
    assert resp.status_code == 201
    assert resp.json()["database_name"] == "nnp_devsecops"


def test_add_db_details_inline_creds_422(client):
    resp = client.post(
        "/manageDataSql/addDBDetails",
        json={
            "bucket_id": _DB["bucket_id"],
            "database_name": "mydb",
            "connection_url": "postgresql://user:secret@host:5432/db",
        },
    )
    assert resp.status_code == 422


def test_add_db_details_invalid_status_422(client):
    resp = client.post(
        "/manageDataSql/addDBDetails",
        json={"bucket_id": _DB["bucket_id"], "database_name": "mydb", "status": "DRAFT"},
    )
    assert resp.status_code == 422


def test_add_db_details_missing_bucket_id_422(client):
    resp = client.post(
        "/manageDataSql/addDBDetails",
        json={"database_name": "mydb"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /manageDataSql/updateDBDetails/{id}
# ---------------------------------------------------------------------------

def test_update_db_details_200(client):
    updated = {**_DB, "status": "INACTIVE"}
    with patch("src.repositories.data_sql_repo.update_database", return_value=updated):
        resp = client.put(
            f"/manageDataSql/updateDBDetails/{_DB['id']}",
            json={"status": "INACTIVE"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INACTIVE"


def test_update_db_details_404_when_not_found(client):
    with patch("src.repositories.data_sql_repo.update_database", return_value=None):
        resp = client.put(
            "/manageDataSql/updateDBDetails/missing",
            json={"status": "ACTIVE"},
        )
    assert resp.status_code == 404


def test_update_db_details_inline_creds_422(client):
    resp = client.put(
        f"/manageDataSql/updateDBDetails/{_DB['id']}",
        json={"connection_url": "postgresql://u:p@host/db"},
    )
    assert resp.status_code == 422


def test_update_db_details_invalid_status_422(client):
    resp = client.put(
        f"/manageDataSql/updateDBDetails/{_DB['id']}",
        json={"status": "PROVISIONING"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /manageDataSql/addSQLDetails
# ---------------------------------------------------------------------------

def test_add_sql_details_201(client):
    with patch("src.repositories.data_sql_repo.create_sql", return_value=_QUERY):
        resp = client.post(
            "/manageDataSql/addSQLDetails",
            json={
                "database_id": _DB["id"],
                "query_name": "Daily signups",
                "query_text": "SELECT 1",
                "rank": 2,
                "status": "DRAFT",
                "quality_score": 1.0,
            },
            headers={"User": "test-user"},
        )
    assert resp.status_code == 201
    assert resp.json()["query_name"] == "Daily signups"


def test_add_sql_details_invalid_rank_422(client):
    resp = client.post(
        "/manageDataSql/addSQLDetails",
        json={"database_id": _DB["id"], "query_name": "Q", "rank": 99},
    )
    assert resp.status_code == 422


def test_add_sql_details_invalid_quality_score_422(client):
    resp = client.post(
        "/manageDataSql/addSQLDetails",
        json={"database_id": _DB["id"], "query_name": "Q", "quality_score": 2.0},
    )
    assert resp.status_code == 422


def test_add_sql_details_status_active_rejected_422(client):
    # SQL queries use CURATION_STATUSES (DRAFT/PUBLISHED/ARCHIVED), not ACTIVE
    resp = client.post(
        "/manageDataSql/addSQLDetails",
        json={"database_id": _DB["id"], "query_name": "Q", "status": "ACTIVE"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /manageDataSql/updateSQLDetails/{id}
# ---------------------------------------------------------------------------

def test_update_sql_details_200(client):
    updated = {**_QUERY, "status": "PUBLISHED"}
    with patch("src.repositories.data_sql_repo.update_sql", return_value=updated):
        resp = client.put(
            f"/manageDataSql/updateSQLDetails/{_QUERY['id']}",
            json={"status": "PUBLISHED"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PUBLISHED"


def test_update_sql_details_404_when_not_found(client):
    with patch("src.repositories.data_sql_repo.update_sql", return_value=None):
        resp = client.put(
            "/manageDataSql/updateSQLDetails/missing",
            json={"status": "PUBLISHED"},
        )
    assert resp.status_code == 404


def test_update_sql_details_invalid_rank_422(client):
    resp = client.put(
        f"/manageDataSql/updateSQLDetails/{_QUERY['id']}",
        json={"rank": 0},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /manageDataSql/deleteDBDetail/{id}
# ---------------------------------------------------------------------------

def test_delete_db_detail_200(client):
    deleted = {**_DB, "status": "DELETED", "queries": []}
    with patch("src.repositories.data_sql_repo.delete_database", return_value=deleted):
        resp = client.delete(f"/manageDataSql/deleteDBDetail/{_DB['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


def test_delete_db_detail_404_when_not_found(client):
    with patch("src.repositories.data_sql_repo.delete_database", return_value=None):
        resp = client.delete("/manageDataSql/deleteDBDetail/missing")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /manageDataSql/deleteSQLDetail/{id}
# ---------------------------------------------------------------------------

def test_delete_sql_detail_200(client):
    deleted = {**_QUERY, "status": "DELETED"}
    with patch("src.repositories.data_sql_repo.delete_sql", return_value=deleted):
        resp = client.delete(f"/manageDataSql/deleteSQLDetail/{_QUERY['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


def test_delete_sql_detail_404_when_not_found(client):
    with patch("src.repositories.data_sql_repo.delete_sql", return_value=None):
        resp = client.delete("/manageDataSql/deleteSQLDetail/missing")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# updateSQLDetails / deleteSQLDetail — Vanna side-effects
# ---------------------------------------------------------------------------

def test_update_sql_details_retrains_vanna(client):
    """Re-trains Vanna when query_context + query_text are present on update."""
    updated = {**_QUERY, "query_context": "How many signups today?", "database_id": _DB["id"]}
    mock_vn = MagicMock()
    with patch("src.repositories.data_sql_repo.update_sql", return_value=updated), \
         patch("src.repositories.data_sql_repo.get_database_by_id", return_value=_DB), \
         patch("src.services.vanna_service.get_vanna",
               new_callable=AsyncMock, return_value=mock_vn):
        resp = client.put(
            f"/manageDataSql/updateSQLDetails/{_QUERY['id']}",
            json={"query_context": "How many signups today?"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 200
    mock_vn.train.assert_called_once_with(
        question="How many signups today?", sql=_QUERY["query_text"]
    )


def test_update_sql_details_vanna_failure_returns_200(client):
    """Vanna re-train failure is swallowed; endpoint still returns 200."""
    updated = {**_QUERY, "query_context": "How many signups today?", "database_id": _DB["id"]}
    with patch("src.repositories.data_sql_repo.update_sql", return_value=updated), \
         patch("src.repositories.data_sql_repo.get_database_by_id", return_value=_DB), \
         patch("src.services.vanna_service.get_vanna",
               new_callable=AsyncMock, side_effect=RuntimeError("vanna unavailable")):
        resp = client.put(
            f"/manageDataSql/updateSQLDetails/{_QUERY['id']}",
            json={"query_context": "How many signups today?"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 200


def test_delete_sql_detail_attempts_vector_cleanup(client):
    """delete_sql_detail calls get_training_data when query_context + query_text are present."""
    deleted = {**_QUERY, "query_context": "How many signups today?", "status": "DELETED"}
    mock_vn = MagicMock()
    mock_vn.get_training_data.return_value = None  # no vectors; cleanup skips safely
    with patch("src.repositories.data_sql_repo.delete_sql", return_value=deleted), \
         patch("src.repositories.data_sql_repo.get_database_by_id", return_value=_DB), \
         patch("src.services.vanna_service.get_vanna",
               new_callable=AsyncMock, return_value=mock_vn):
        resp = client.delete(f"/manageDataSql/deleteSQLDetail/{_QUERY['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"
    mock_vn.get_training_data.assert_called_once()
