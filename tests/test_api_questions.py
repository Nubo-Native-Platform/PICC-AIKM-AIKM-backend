"""API-layer tests for /manageQuestions."""

from unittest.mock import patch

_QA = {
    "id": "33333333-3333-3333-3333-333333333333",
    "bucket_id": "11111111-1111-1111-1111-111111111111",
    "question": "What is NNP?",
    "answer": "A platform.",
    "rank": 2,
    "status": "DRAFT",
    "match_threshold": None,
    "question_embedding_id": None,
}


# ---------------------------------------------------------------------------
# GET /manageQuestions/getDetails
# ---------------------------------------------------------------------------

def test_get_details_returns_list(client):
    with patch("src.repositories.question_repo.get_by_buckets", return_value=[_QA]):
        resp = client.get(f"/manageQuestions/getDetails?bucketIds={_QA['bucket_id']}")
    assert resp.status_code == 200
    assert resp.json()[0]["question"] == "What is NNP?"


def test_get_details_missing_bucket_ids_422(client):
    # bucketIds is a required query param
    resp = client.get("/manageQuestions/getDetails")
    assert resp.status_code == 422


def test_get_details_comma_separated_ids(client):
    ids = "aaaa,bbbb,cccc"
    with patch("src.repositories.question_repo.get_by_buckets", return_value=[]) as mock_fn:
        client.get(f"/manageQuestions/getDetails?bucketIds={ids}")
    passed_ids, _ = mock_fn.call_args.args
    assert passed_ids == ["aaaa", "bbbb", "cccc"]


# ---------------------------------------------------------------------------
# POST /manageQuestions/addQDetails
# ---------------------------------------------------------------------------

def test_add_q_details_201(client):
    with patch("src.repositories.question_repo.create", return_value=_QA):
        resp = client.post(
            "/manageQuestions/addQDetails",
            json={"bucket_id": _QA["bucket_id"], "question": "What is NNP?", "answer": "A platform.", "rank": 2},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 201


def test_add_q_details_invalid_rank_422(client):
    resp = client.post(
        "/manageQuestions/addQDetails",
        json={"bucket_id": _QA["bucket_id"], "question": "Q?", "answer": "A", "rank": 10},
    )
    assert resp.status_code == 422


def test_add_q_details_invalid_status_422(client):
    resp = client.post(
        "/manageQuestions/addQDetails",
        json={"bucket_id": _QA["bucket_id"], "question": "Q?", "answer": "A", "status": "ACTIVE"},
    )
    assert resp.status_code == 422


def test_add_q_details_missing_required_fields_422(client):
    resp = client.post(
        "/manageQuestions/addQDetails",
        json={"bucket_id": _QA["bucket_id"]},   # question + answer are required
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /manageQuestions/updateQDetails/{id}
# ---------------------------------------------------------------------------

def test_update_q_details_200(client):
    updated = {**_QA, "status": "PUBLISHED"}
    with patch("src.repositories.question_repo.update", return_value=updated):
        resp = client.put(
            f"/manageQuestions/updateQDetails/{_QA['id']}",
            json={"status": "PUBLISHED"},
            headers={"User": "test-user"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PUBLISHED"


def test_update_q_details_404_when_not_found(client):
    with patch("src.repositories.question_repo.update", return_value=None):
        resp = client.put(
            "/manageQuestions/updateQDetails/missing",
            json={"status": "PUBLISHED"},
        )
    assert resp.status_code == 404


def test_update_q_details_invalid_rank_422(client):
    resp = client.put(
        f"/manageQuestions/updateQDetails/{_QA['id']}",
        json={"rank": 0},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /manageQuestions/deleteQDetail/{id}
# ---------------------------------------------------------------------------

def test_delete_q_detail_200(client):
    deleted = {**_QA, "status": "DELETED"}
    with patch("src.repositories.question_repo.delete", return_value=deleted):
        resp = client.delete(f"/manageQuestions/deleteQDetail/{_QA['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"


def test_delete_q_detail_404_when_not_found(client):
    with patch("src.repositories.question_repo.delete", return_value=None):
        resp = client.delete("/manageQuestions/deleteQDetail/missing")
    assert resp.status_code == 404
