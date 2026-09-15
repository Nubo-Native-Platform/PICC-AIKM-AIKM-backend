"""Vanna NL->SQL service using PGVector + Ollama (NEW).

One NNPVanna instance per registered database, cached in memory.
Vector storage : PGVector (langchain_pg_* tables in Postgres)
LLM            : Ollama (local server, model configurable via LLM_MODEL setting)
Embeddings     : configured by VANNA_PUBLIC_EMBEDDING_MODEL / VANNA_LOCAL_EMBEDDING_MODEL

parse_training_script / validate_sql / AREA_LABELS live here (moved from
the now-deleted sql_generator.py).
"""

import asyncio
import re

from vanna.pgvector import PG_VectorStore
from vanna.ollama import Ollama

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── helpers moved from sql_generator.py ──────────────────────────────────────

AREA_LABELS = {
    "Infra": "Infrastructure",
    "DevOps": "DevOps and CI/CD",
    "Security": "Security",
    "Application": "Application",
    "Business": "Business",
    "Analytics": "Analytics",
    "Other": "General",
}

_RE_SEC1 = re.compile(r"^--\s*(SECTION 1|──\s*SCHEMA)\s*$", re.IGNORECASE)
_RE_SEC2 = re.compile(r"^--\s*(SECTION 2|──\s*BUSINESS RULES)\s*$", re.IGNORECASE)
_RE_SEC3 = re.compile(r"^--\s*SECTION 3\s*$", re.IGNORECASE)
_RE_Q = re.compile(r"^--\s*Q:\s*(.+)$")
_RE_A = re.compile(r"^--\s*A:\s*(.+)$")


def parse_training_script(script: str) -> dict:
    """Parse the structured training script into schema, rules, and Q→SQL examples.

    Handles both "-- SECTION N" and "-- ── SECTION NAME" marker styles.
    Returns {"schema": str, "rules": str, "examples": list[{"question", "sql"}]}.
    Never raises.
    """
    try:
        lines = script.splitlines()
        schema_start = rules_start = examples_start = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if _RE_SEC1.match(stripped):
                schema_start = i + 1
            elif _RE_SEC2.match(stripped):
                rules_start = i + 1
            elif _RE_SEC3.match(stripped):
                examples_start = i + 1

        if schema_start >= 0:
            end = (rules_start - 1) if rules_start > schema_start else (
                examples_start - 1 if examples_start > schema_start else len(lines)
            )
            schema = "\n".join(lines[schema_start:end]).strip()
        else:
            schema = script.strip()

        if rules_start >= 0:
            end = (examples_start - 1) if examples_start > rules_start else len(lines)
            rules = "\n".join(lines[rules_start:end]).strip()
        else:
            rules = ""

        examples: list[dict] = []
        i = 0
        while i < len(lines):
            q_match = _RE_Q.match(lines[i].strip())
            if q_match:
                question = q_match.group(1).strip()
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    a_match = _RE_A.match(lines[j].strip())
                    if a_match:
                        examples.append({"question": question, "sql": a_match.group(1).strip()})
                        i = j + 1
                        continue
            i += 1

        return {"schema": schema, "rules": rules, "examples": examples}
    except Exception as exc:  # noqa: BLE001
        logger.error("parse_training_script error: %s", exc)
        return {"schema": "", "rules": "", "examples": []}


def validate_sql(sql: str) -> bool:
    """Return True if sql starts with SELECT (case-insensitive, ignoring backticks)."""
    clean = sql.strip().strip("`").strip()
    return clean.upper().startswith("SELECT")


# ── Vanna instance management ─────────────────────────────────────────────────

_vanna_cache: dict[str, "NNPVanna"] = {}


class NNPVanna(PG_VectorStore, Ollama):
    def __init__(self, config=None):
        prefix = config.get("collection_name", "nnp") if config else "nnp"

        PG_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

        from langchain_postgres import PGVector
        conn = config.get("connection_string", "") if config else ""
        emb = self.embedding_function

        self.sql_collection = PGVector(
            embeddings=emb,
            collection_name=f"{prefix}_sql",
            connection=conn,
        )
        self.ddl_collection = PGVector(
            embeddings=emb,
            collection_name=f"{prefix}_ddl",
            connection=conn,
        )
        self.documentation_collection = PGVector(
            embeddings=emb,
            collection_name=f"{prefix}_documentation",
            connection=conn,
        )


def _get_vanna_sync(db_id: str) -> "NNPVanna":
    """Get or create a Vanna instance for a specific database (sync, call via to_thread)."""
    from src.repositories import data_sql_repo
    db_record = data_sql_repo.get_database_by_id(db_id)
    backend = (db_record or {}).get("vanna_embedding_backend") or "openai"
    if not settings.ollama_base_url:
        raise ValueError(
            "OLLAMA_BASE_URL not configured. "
            "SQL generation unavailable."
        )
    if not settings.pg_connection_string_vanna:
        raise ValueError(
            "PG_CONNECTION_STRING_VANNA not configured. "
            "SQL generation unavailable."
        )
    if db_id not in _vanna_cache:
        prefix = "nnp_local" if backend == "local" else "nnp"
        collection = f"{prefix}_{db_id[:8]}"
        conn_str = settings.pg_connection_string_vanna
        if "search_path" not in conn_str and "options=" not in conn_str:
            if "?" in conn_str:
                conn_str += "&options=-csearch_path%3Dnnp-rag,public"
            else:
                conn_str += "?options=-csearch_path%3Dnnp-rag,public"
        if backend == "local":
            from langchain_huggingface import HuggingFaceEmbeddings
            embedding_fn = HuggingFaceEmbeddings(
                model_name=settings.vanna_local_embedding_model,
                encode_kwargs={"normalize_embeddings": True},
            )
        else:
            from langchain_openai import OpenAIEmbeddings
            embedding_fn = OpenAIEmbeddings(
                model=settings.vanna_public_embedding_model,
                openai_api_key=settings.openai_api_key,
            )
        config = {
            "model": settings.llm_model,
            "ollama_host": settings.ollama_base_url,
            "keep_alive": settings.ollama_keep_alive,
            "options": {"num_ctx": settings.ollama_num_ctx},
            "connection_string": conn_str,
            "n_results": settings.vanna_n_results,
            "collection_name": collection,
            "embedding_function": embedding_fn,
        }
        logger.info("[vanna] creating instance db_id=%s collection=%s", db_id, collection)
        _vanna_cache[db_id] = NNPVanna(config=config)
    return _vanna_cache[db_id]


async def get_vanna(db_id: str) -> "NNPVanna":
    """Async wrapper — returns the cached NNPVanna instance for a database."""
    return await asyncio.to_thread(_get_vanna_sync, db_id)


# ── Training ──────────────────────────────────────────────────────────────────

def _drop_temp_collections(conn_str: str, new_prefix: str) -> None:
    """Drop the temporary _new training collections on failure or empty result."""
    try:
        from sqlalchemy import create_engine, text as sa_text
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            conn.execute(sa_text("""
                DELETE FROM "nnp-rag".langchain_pg_embedding e
                USING "nnp-rag".langchain_pg_collection c
                WHERE e.collection_id = c.uuid AND c.name LIKE :pattern
            """), {"pattern": f"{new_prefix}%"})
            conn.execute(sa_text("""
                DELETE FROM "nnp-rag".langchain_pg_collection
                WHERE name LIKE :pattern
            """), {"pattern": f"{new_prefix}%"})
            conn.commit()
        engine.dispose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[vanna] failed to drop temp collections %s: %s", new_prefix, exc)


def _train_sync(
    db_id: str,
    training_script: str,
    db_name: str | None,
    db_type: str | None,
    area: str | None,
) -> int:
    """Parse training_script and write vectors with an insert-first strategy.

    New vectors go into _new_ temp collections first. Only after all insertions
    succeed are the old production collections deleted and the new ones renamed
    atomically, preventing any query window where vectors are absent.
    """
    from src.repositories import data_sql_repo
    db_record = data_sql_repo.get_database_by_id(db_id)
    backend = (db_record or {}).get("vanna_embedding_backend") or "openai"
    parsed = parse_training_script(training_script)
    base_prefix = "nnp_local" if backend == "local" else "nnp"
    prefix = f"{base_prefix}_{db_id[:8]}"
    new_prefix = f"{prefix}_new"
    count = 0

    # Step 1 — Build a temp NNPVanna instance targeting the _new collections
    conn_str = settings.pg_connection_string_vanna
    if "search_path" not in conn_str and "options=" not in conn_str:
        conn_str += ("&" if "?" in conn_str else "?") + "options=-csearch_path%3Dnnp-rag,public"
    if backend == "local":
        from langchain_huggingface import HuggingFaceEmbeddings
        embedding_fn = HuggingFaceEmbeddings(
            model_name=settings.vanna_local_embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
    else:
        from langchain_openai import OpenAIEmbeddings
        embedding_fn = OpenAIEmbeddings(
            model=settings.vanna_public_embedding_model,
            openai_api_key=settings.openai_api_key,
        )
    new_vn = NNPVanna(config={
        "model": settings.llm_model,
        "ollama_host": settings.ollama_base_url,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"num_ctx": settings.ollama_num_ctx},
        "connection_string": conn_str,
        "n_results": settings.vanna_n_results,
        "collection_name": new_prefix,
        "embedding_function": embedding_fn,
    })
    logger.info("[vanna] training into temp collections prefix=%s db=%s", new_prefix, db_id)

    # Step 2 — Insert all new vectors into the _new collections
    inserted_any = False

    if parsed["schema"]:
        try:
            new_vn.train(ddl=parsed["schema"])
            inserted_any = True
            logger.info("[vanna] trained DDL into temp db=%s", db_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("[vanna] DDL train failed db=%s: %s", db_id, exc)

    if parsed["rules"]:
        try:
            new_vn.train(documentation=parsed["rules"])
            inserted_any = True
            logger.info("[vanna] trained rules into temp db=%s", db_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("[vanna] rules train failed db=%s: %s", db_id, exc)

    for ex in parsed.get("examples", []):
        try:
            new_vn.train(question=ex["question"], sql=ex["sql"])
            count += 1
            inserted_any = True
        except Exception as exc:  # noqa: BLE001
            logger.error("[vanna] example train failed db=%s: %s", db_id, exc)

    if not inserted_any:
        logger.warning("[vanna] nothing inserted for db=%s — skipping swap, cleaning up", db_id)
        _drop_temp_collections(conn_str, new_prefix)
        return 0

    # Step 3 — Atomic swap: delete old production vectors, rename _new → production
    try:
        from sqlalchemy import create_engine, text as sa_text
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            # Delete old production embeddings
            for suffix in ("_sql", "_ddl", "_documentation"):
                conn.execute(sa_text("""
                    DELETE FROM "nnp-rag".langchain_pg_embedding e
                    USING "nnp-rag".langchain_pg_collection c
                    WHERE e.collection_id = c.uuid AND c.name = :name
                """), {"name": f"{prefix}{suffix}"})
            # Delete old production collection rows
            conn.execute(sa_text("""
                DELETE FROM "nnp-rag".langchain_pg_collection
                WHERE name IN (:sql, :ddl, :doc)
            """), {
                "sql": f"{prefix}_sql",
                "ddl": f"{prefix}_ddl",
                "doc": f"{prefix}_documentation",
            })
            # Rename _new_ collections to production names atomically
            conn.execute(sa_text("""
                UPDATE "nnp-rag".langchain_pg_collection
                SET name = REPLACE(name, :needle, :replacement)
                WHERE name LIKE :pattern
            """), {
                "needle": f"{new_prefix}_",
                "replacement": f"{prefix}_",
                "pattern": f"{new_prefix}%",
            })
            conn.commit()
        engine.dispose()
        logger.info("[vanna] atomic swap complete db=%s examples=%d", db_id, count)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[vanna] atomic swap failed db=%s: %s — new vectors remain in %s",
            db_id, exc, new_prefix,
        )

    logger.info("[vanna] training complete db=%s examples=%d", db_id, count)
    return count


async def train_from_script(
    db_id: str,
    training_script: str,
    db_name: str | None = None,
    db_type: str | None = None,
    area: str | None = None,
) -> None:
    """Parse and train Vanna from training_script. Called as a background task.

    Never raises.
    """
    try:
        if not training_script:
            logger.info("[vanna] no training_script for db=%s, skipping", db_id)
            return
        count = await asyncio.to_thread(
            _train_sync, db_id, training_script, db_name, db_type, area
        )
        logger.info("[vanna] train_from_script done db=%s count=%d", db_id, count)
        # Clear cached instance so next query gets a fresh instance with new vectors
        if db_id in _vanna_cache:
            del _vanna_cache[db_id]
            logger.info("[vanna] cache cleared after training db_id=%s", db_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[vanna] train_from_script failed db=%s: %s", db_id, exc)


async def clear_training(db_id: str) -> None:
    """Remove all Vanna training data for a database. Called on soft-delete.

    Never raises.
    """
    try:
        def _clear() -> None:
            vn = _get_vanna_sync(db_id)
            try:
                df = vn.get_training_data()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        try:
                            vn.remove_training_data(id=str(row.get("id", "")))
                        except Exception:  # noqa: BLE001
                            pass
                    logger.info("[vanna] cleared %d training items for db=%s", len(df), db_id)
                else:
                    logger.info("[vanna] no training data to clear for db=%s", db_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[vanna] clear failed for db=%s: %s", db_id, exc)
            finally:
                _vanna_cache.pop(db_id, None)

        await asyncio.to_thread(_clear)
    except Exception as exc:  # noqa: BLE001
        logger.error("[vanna] clear_training error db=%s: %s", db_id, exc)


# ── Query ─────────────────────────────────────────────────────────────────────

def _query_sync(question: str, db_id: str) -> tuple[str | None, str | None]:
    """Call Vanna to generate SQL. Returns (sql, error_msg). Sync — call via to_thread."""
    vn = _get_vanna_sync(db_id)
    try:
        sql = vn.generate_sql(question=question)
        if not sql:
            return None, "No SQL generated"
        clean = sql.strip().strip("`").strip()
        if not validate_sql(clean):
            return None, f"Non-SELECT generated: {clean[:100]}"
        return clean, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


async def generate_sql(
    question: str,
    db_id: str,
) -> tuple[str | None, str | None]:
    """Async SQL generation via Vanna. Returns (sql, error_msg). Never raises."""
    try:
        return await asyncio.to_thread(_query_sync, question, db_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("[vanna] generate_sql failed db=%s: %s", db_id, exc)
        return None, str(exc)
