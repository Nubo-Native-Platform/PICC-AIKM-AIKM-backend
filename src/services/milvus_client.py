"""Direct Milvus collection management (NEW).

Called from the manageBucket router as background tasks for collection
create/delete. All public functions are async; pymilvus blocking I/O is
delegated to a thread via asyncio.to_thread so the event loop is not blocked.

Connection pattern: connect in the worker thread → operate → disconnect.
Each function never raises — all exceptions are caught and returned as
(False, message) or False.
"""

import asyncio
from typing import Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_ALIAS = "km_milvus"
_EMBEDDING_DIM = 3072


def _connect() -> None:
    connections.connect(
        alias=_ALIAS,
        host=settings.milvus_host,
        port=settings.milvus_port,
        db_name=settings.milvus_db_name,
    )


def _disconnect() -> None:
    try:
        connections.disconnect(_ALIAS)
    except Exception:
        pass


def _create_collection_sync(collection_name: str, dim: int = _EMBEDDING_DIM) -> tuple[bool, Optional[str]]:
    try:
        _connect()
        if utility.has_collection(collection_name, using=_ALIAS):
            return True, None
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]
        schema = CollectionSchema(fields=fields, enable_dynamic_field=False)
        collection = Collection(name=collection_name, schema=schema, using=_ALIAS)
        collection.create_index(
            field_name="embedding",
            index_params={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 12, "efConstruction": 200},
            },
        )
        collection.load()
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        _disconnect()


def _delete_collection_sync(collection_name: str) -> tuple[bool, Optional[str]]:
    try:
        _connect()
        if not utility.has_collection(collection_name, using=_ALIAS):
            return True, None
        utility.drop_collection(collection_name, using=_ALIAS)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        _disconnect()


def _collection_exists_sync(collection_name: str) -> bool:
    try:
        _connect()
        return utility.has_collection(collection_name, using=_ALIAS)
    except Exception:  # noqa: BLE001
        return False
    finally:
        _disconnect()


async def create_collection(collection_name: str, dim: int = _EMBEDDING_DIM) -> tuple[bool, Optional[str]]:
    """Create a Milvus collection with the standard KM schema.

    Returns (True, None) on success, (False, error_message) on failure.
    Never raises.
    """
    return await asyncio.to_thread(_create_collection_sync, collection_name, dim)


async def delete_collection(collection_name: str) -> tuple[bool, Optional[str]]:
    """Drop a Milvus collection. Idempotent — missing collection → (True, None).

    Returns (True, None) on success, (False, error_message) on failure.
    Never raises.
    """
    return await asyncio.to_thread(_delete_collection_sync, collection_name)


async def collection_exists(collection_name: str) -> bool:
    """Return True if the collection exists in Milvus; False on any error."""
    return await asyncio.to_thread(_collection_exists_sync, collection_name)


def _insert_vectors_sync(collection_name: str, entities: list) -> tuple[bool, Optional[str]]:
    try:
        _connect()
        col = Collection(name=collection_name, using=_ALIAS)
        col.insert(entities)
        col.flush()
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        _disconnect()


def _delete_by_source_sync(collection_name: str, source_id: str) -> tuple[bool, Optional[str]]:
    try:
        _connect()
        col = Collection(name=collection_name, using=_ALIAS)
        col.delete(f'source == "{source_id}"')
        col.flush()
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        _disconnect()


async def insert_vectors(collection_name: str, entities: list) -> tuple[bool, Optional[str]]:
    """Insert entity dicts into a collection. Returns (True, None) on success.

    Never raises.
    """
    return await asyncio.to_thread(_insert_vectors_sync, collection_name, entities)


async def delete_by_source(collection_name: str, source_id: str) -> tuple[bool, Optional[str]]:
    """Delete all vectors where source == source_id. Returns (True, None) on success.

    Never raises.
    """
    return await asyncio.to_thread(_delete_by_source_sync, collection_name, source_id)
