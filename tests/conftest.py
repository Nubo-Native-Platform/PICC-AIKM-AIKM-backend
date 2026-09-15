"""Shared test fixtures.

The TestClient triggers the FastAPI lifespan (which calls pool.init_pool).
We patch that out so tests never need a real database connection.

Background task isolation:
- provision_client / ingestion_client are already no-ops (PROVISION_ENABLED /
  INGESTION_ENABLED are false by default).
- vanna_service.clear_training and sql_query_service.train_from_script are
  patched to AsyncMock so the deleteDBDetail / addDBDetails / updateDBDetails
  background tasks never touch the real PGVector database during tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="session")
def client():
    with (
        patch("src.db.pool.init_pool"),
        patch("src.db.pool.close_pool"),
        patch("src.services.vanna_service.clear_training", new=AsyncMock()),
        patch("src.services.sql_query_service.train_from_script", new=AsyncMock()),
    ):
        with TestClient(app) as c:
            yield c
