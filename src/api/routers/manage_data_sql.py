"""manageDataSql router (NEW). Tables: nnp_km_database + nnp_database_q.

After a database is created or updated, a background task fires to push the
training_script to the SQL query service (Vanna). If the service is
unavailable the task logs and swallows the error — CRUD is never blocked.
"""

import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from src.api.deps import current_user
from src.models.data_sql import (
    DatabaseCreate,
    DatabaseUpdate,
    DDLCreate,
    DDLUpdate,
    RuleCreate,
    RuleUpdate,
    SqlQueryCreate,
    SqlQueryUpdate,
)
from src.repositories import data_sql_repo, ddl_rule_repo
from src.utils.logger import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/manageDataSql", tags=["manageDataSql"])


async def _delete_db_vectors_task(db_id: str) -> None:
    try:
        from src.services import vanna_service
        await vanna_service.clear_training(db_id)
    except Exception as exc:
        log.error("_delete_db_vectors_task: error for db %s: %s", db_id, exc)


async def _train_database_task(
    db_id: str,
    training_script: str | None,
    db_name: str | None,
    db_type: str | None,
    area: str | None,
) -> None:
    if not training_script:
        log.debug("_train_database_task: no training_script for db %s, skipping", db_id)
        return
    try:
        from src.services import sql_query_service
        await sql_query_service.train_from_script(
            db_id, training_script, db_name, db_type, area
        )
        log.info("_train_database_task: trained db %s successfully", db_id)
    except Exception as exc:
        log.error("_train_database_task: failed for db %s: %s", db_id, exc)


@router.get("/getDetails")
async def get_details(bucketIds: str, includeDeleted: bool = False):
    """Return registered databases (with their nested saved queries) for buckets.

    bucketIds is a comma-separated list of bucket UUIDs.
    """
    ids = [b for b in (bucketIds or "").split(",") if b.strip()]
    return await run_in_threadpool(data_sql_repo.get_by_buckets, ids, includeDeleted)


# ---- databases (nnp_km_database) ----------------------------------------

@router.post("/addDBDetails", status_code=201)
async def add_db_details(
    payload: DatabaseCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Register a database. connection_url must be credential-less."""
    user = current_user(request)
    row = await run_in_threadpool(data_sql_repo.create_database, payload.model_dump(), user)
    background_tasks.add_task(
        _train_database_task,
        str(row["id"]),
        row.get("training_script"),
        row.get("database_name"),
        row.get("database_type"),
        row.get("area"),
    )
    return row


@router.delete("/deleteDBDetail/{db_id}")
async def delete_db_detail(db_id: str, background_tasks: BackgroundTasks):
    """Soft-delete a registered database (status → DELETED).

    Best-effort: removes all Milvus vectors for this database in the background.
    """
    row = await run_in_threadpool(data_sql_repo.delete_database, db_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Database not found")
    background_tasks.add_task(_delete_db_vectors_task, db_id)
    return row


@router.put("/updateDBDetails/{db_id}")
async def update_db_details(
    db_id: str,
    payload: DatabaseUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Update a registered database."""
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    row = await run_in_threadpool(data_sql_repo.update_database, db_id, data, user)
    if row is None:
        raise HTTPException(status_code=404, detail="Database not found")
    background_tasks.add_task(
        _train_database_task,
        str(row["id"]),
        row.get("training_script"),
        row.get("database_name"),
        row.get("database_type"),
        row.get("area"),
    )
    return row


# ---- saved queries (nnp_database_q) -------------------------------------

@router.post("/addSQLDetails", status_code=201)
async def add_sql_details(payload: SqlQueryCreate, request: Request):
    """Create a saved query and train it into Vanna if question + SQL are provided."""
    user = current_user(request)
    row = await run_in_threadpool(data_sql_repo.create_sql, payload.model_dump(), user)

    if payload.query_context and payload.query_text:
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(data_sql_repo.get_database_by_id, payload.database_id)
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                await asyncio.to_thread(vn.train, question=payload.query_context, sql=payload.query_text)
                log.info("[addSQLDetails] trained via Vanna for db=%s", str(db["id"]))
        except Exception as exc:  # noqa: BLE001
            log.error("[addSQLDetails] Vanna train failed: %s", exc)

    return row


@router.delete("/deleteSQLDetail/{sql_id}")
async def delete_sql_detail(sql_id: str):
    """Soft-delete a saved query (status → DELETED)."""
    row = await run_in_threadpool(data_sql_repo.delete_sql, sql_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    if row.get("query_context") and row.get("query_text"):
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(
                data_sql_repo.get_database_by_id, str(row["database_id"])
            )
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                df = await asyncio.to_thread(vn.get_training_data)
                if df is not None and not df.empty:
                    matches = df[
                        (df["question"] == row["query_context"]) &
                        (df["sql"] == row["query_text"])
                    ]
                    if not matches.empty:
                        await asyncio.to_thread(
                            vn.remove_training_data, id=str(matches.iloc[0]["id"])
                        )
                        log.info("[deleteSQLDetail] removed vector for db=%s", db["id"])
                    else:
                        log.warning("[deleteSQLDetail] no vector found for db=%s", db["id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("[deleteSQLDetail] vector cleanup failed: %s", exc)

    return row


@router.put("/updateSQLDetails/{sql_id}")
async def update_sql_details(sql_id: str, payload: SqlQueryUpdate, request: Request):
    """Update a saved query."""
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    row = await run_in_threadpool(data_sql_repo.update_sql, sql_id, data, user)
    if row is None:
        raise HTTPException(status_code=404, detail="Saved query not found")

    if row.get("query_context") and row.get("query_text"):
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(
                data_sql_repo.get_database_by_id, str(row["database_id"])
            )
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                await asyncio.to_thread(
                    vn.train, question=row["query_context"], sql=row["query_text"]
                )
                log.info("[updateSQLDetails] re-trained for db=%s", db["id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("[updateSQLDetails] re-train failed: %s", exc)

    return row


# ---- DDL entries (nnp_database_ddl) -------------------------------------

@router.post("/addDDLDetails", status_code=201)
async def add_ddl_details(payload: DDLCreate, request: Request):
    """Create a DDL entry and train it into Vanna."""
    user = current_user(request)
    row = await run_in_threadpool(ddl_rule_repo.create_ddl, payload.model_dump(), user)

    try:
        from src.services import vanna_service
        db = await run_in_threadpool(data_sql_repo.get_database_by_id, payload.database_id)
        if db:
            vn = await vanna_service.get_vanna(str(db["id"]))
            vector_id = await asyncio.to_thread(vn.train, ddl=payload.ddl_text)
            updated = await run_in_threadpool(
                ddl_rule_repo.update_ddl, str(row["id"]), {"vanna_vector_id": vector_id}, user
            )
            if updated:
                row = updated
            log.info("[addDDLDetails] trained DDL for db=%s vector_id=%s", db["id"], vector_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[addDDLDetails] Vanna train failed: %s", exc)

    return row


@router.put("/updateDDLDetails/{ddl_id}")
async def update_ddl_details(ddl_id: str, payload: DDLUpdate, request: Request):
    """Update a DDL entry. Re-trains Vanna when ddl_text changes."""
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    row = await run_in_threadpool(ddl_rule_repo.update_ddl, ddl_id, data, user)
    if row is None:
        raise HTTPException(status_code=404, detail="DDL entry not found")

    if payload.ddl_text is not None:
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(
                data_sql_repo.get_database_by_id, str(row["database_id"])
            )
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                if row.get("vanna_vector_id"):
                    await asyncio.to_thread(vn.remove_training_data, id=row["vanna_vector_id"])
                new_id = await asyncio.to_thread(vn.train, ddl=row["ddl_text"])
                updated = await run_in_threadpool(
                    ddl_rule_repo.update_ddl, ddl_id, {"vanna_vector_id": new_id}, user
                )
                if updated:
                    row = updated
                log.info("[updateDDLDetails] re-trained for db=%s new_vector=%s", db["id"], new_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("[updateDDLDetails] Vanna re-train failed: %s", exc)

    return row


@router.delete("/deleteDDLDetail/{ddl_id}")
async def delete_ddl_detail(ddl_id: str):
    """Soft-delete a DDL entry and remove its Vanna vector."""
    row = await run_in_threadpool(ddl_rule_repo.delete_ddl, ddl_id)
    if row is None:
        raise HTTPException(status_code=404, detail="DDL entry not found")

    if row.get("vanna_vector_id"):
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(
                data_sql_repo.get_database_by_id, str(row["database_id"])
            )
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                await asyncio.to_thread(vn.remove_training_data, id=row["vanna_vector_id"])
                log.info("[deleteDDLDetail] removed vector for db=%s", db["id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("[deleteDDLDetail] vector cleanup failed: %s", exc)

    return row


# ---- Rule entries (nnp_database_rule) -----------------------------------

@router.post("/addRuleDetails", status_code=201)
async def add_rule_details(payload: RuleCreate, request: Request):
    """Create a business rule entry and train it into Vanna."""
    user = current_user(request)
    row = await run_in_threadpool(ddl_rule_repo.create_rule, payload.model_dump(), user)

    try:
        from src.services import vanna_service
        db = await run_in_threadpool(data_sql_repo.get_database_by_id, payload.database_id)
        if db:
            vn = await vanna_service.get_vanna(str(db["id"]))
            vector_id = await asyncio.to_thread(vn.train, documentation=payload.rule_text)
            updated = await run_in_threadpool(
                ddl_rule_repo.update_rule, str(row["id"]), {"vanna_vector_id": vector_id}, user
            )
            if updated:
                row = updated
            log.info("[addRuleDetails] trained rule for db=%s vector_id=%s", db["id"], vector_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[addRuleDetails] Vanna train failed: %s", exc)

    return row


@router.put("/updateRuleDetails/{rule_id}")
async def update_rule_details(rule_id: str, payload: RuleUpdate, request: Request):
    """Update a business rule entry. Re-trains Vanna when rule_text changes."""
    user = current_user(request)
    data = payload.model_dump(exclude_unset=True)
    row = await run_in_threadpool(ddl_rule_repo.update_rule, rule_id, data, user)
    if row is None:
        raise HTTPException(status_code=404, detail="Rule entry not found")

    if payload.rule_text is not None:
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(
                data_sql_repo.get_database_by_id, str(row["database_id"])
            )
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                if row.get("vanna_vector_id"):
                    await asyncio.to_thread(vn.remove_training_data, id=row["vanna_vector_id"])
                new_id = await asyncio.to_thread(vn.train, documentation=row["rule_text"])
                updated = await run_in_threadpool(
                    ddl_rule_repo.update_rule, rule_id, {"vanna_vector_id": new_id}, user
                )
                if updated:
                    row = updated
                log.info("[updateRuleDetails] re-trained for db=%s new_vector=%s", db["id"], new_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("[updateRuleDetails] Vanna re-train failed: %s", exc)

    return row


@router.delete("/deleteRuleDetail/{rule_id}")
async def delete_rule_detail(rule_id: str):
    """Soft-delete a rule entry and remove its Vanna vector."""
    row = await run_in_threadpool(ddl_rule_repo.delete_rule, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Rule entry not found")

    if row.get("vanna_vector_id"):
        try:
            from src.services import vanna_service
            db = await run_in_threadpool(
                data_sql_repo.get_database_by_id, str(row["database_id"])
            )
            if db:
                vn = await vanna_service.get_vanna(str(db["id"]))
                await asyncio.to_thread(vn.remove_training_data, id=row["vanna_vector_id"])
                log.info("[deleteRuleDetail] removed vector for db=%s", db["id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("[deleteRuleDetail] vector cleanup failed: %s", exc)

    return row
