import asyncio
import sys
sys.path.insert(0, ".")  # allow running from project root

from src.db import pool
from src.repositories import data_sql_repo, ddl_rule_repo
from src.services import vanna_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def migrate_database(db_id: str) -> None:
    """Re-train one database's DDL/Rules/Queries into local-embedding
    PGVector collections. Does NOT touch the existing OpenAI collections."""

    db = data_sql_repo.get_database_by_id(db_id)
    if not db:
        print(f"ERROR: database {db_id} not found")
        return

    print(f"Migrating: {db['database_name']} (db_id={db_id})")

    if db.get("vanna_embedding_backend") == "local":
        print("  WARNING: vanna_embedding_backend is already 'local' in Postgres.")
        print("  This means _get_vanna_sync will route to nnp_local_* collections.")
        confirm = input("  Continue anyway? (y/n): ")
        if confirm.lower() != "y":
            print("  Aborted.")
            return

    # Force local backend for this migration run regardless of current DB flag,
    # by monkey-patching the db record temporarily — simplest approach for a
    # one-time script. We do this by calling vanna_service internals directly
    # rather than relying on the flag (since the flag may still be 'openai'
    # at this point — we flip it AFTER migration succeeds).

    from src.config.settings import settings
    from langchain_huggingface import HuggingFaceEmbeddings

    collection_prefix = f"nnp_local_{db_id[:8]}"
    conn_str = settings.pg_connection_string_vanna
    if "search_path" not in conn_str and "options=" not in conn_str:
        conn_str += ("&" if "?" in conn_str else "?") + "options=-csearch_path%3Dnnp-rag,public"

    embedding_fn = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True},
    )

    config = {
        "model": settings.llm_model,
        "ollama_host": settings.ollama_base_url,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"num_ctx": settings.ollama_num_ctx},
        "connection_string": conn_str,
        "n_results": settings.vanna_n_results,
        "collection_name": collection_prefix,
        "embedding_function": embedding_fn,
    }
    vn = vanna_service.NNPVanna(config=config)

    # --- DDL ---
    ddl_entries = ddl_rule_repo.get_ddl_by_database(db_id)
    print(f"  DDL entries: {len(ddl_entries)}")
    ddl_count = 0
    for entry in ddl_entries:
        if entry.get("ddl_text"):
            try:
                vn.train(ddl=entry["ddl_text"])
                ddl_count += 1
            except Exception as exc:
                print(f"    FAILED ddl id={entry['id']}: {exc}")
    print(f"  DDL trained: {ddl_count}/{len(ddl_entries)}")

    # --- Rules ---
    rule_entries = ddl_rule_repo.get_rules_by_database(db_id)
    print(f"  Rule entries: {len(rule_entries)}")
    rule_count = 0
    for entry in rule_entries:
        if entry.get("rule_text"):
            try:
                vn.train(documentation=entry["rule_text"])
                rule_count += 1
            except Exception as exc:
                print(f"    FAILED rule id={entry['id']}: {exc}")
    print(f"  Rules trained: {rule_count}/{len(rule_entries)}")

    # --- Queries ---
    query_entries = data_sql_repo.get_sql_by_database(db_id)
    print(f"  Query entries: {len(query_entries)}")
    query_count = 0
    for entry in query_entries:
        if entry.get("query_context") and entry.get("query_text"):
            try:
                vn.train(question=entry["query_context"], sql=entry["query_text"])
                query_count += 1
            except Exception as exc:
                print(f"    FAILED query id={entry['id']}: {exc}")
    print(f"  Queries trained: {query_count}/{len(query_entries)}")

    print(f"\nMigration complete for {db['database_name']}.")
    print(f"New collections: {collection_prefix}_ddl, {collection_prefix}_documentation, {collection_prefix}_sql")
    print(f"Total vectors trained: {ddl_count + rule_count + query_count}")
    print(f"\nNOTE: vanna_embedding_backend flag NOT changed yet. Verify the new")
    print(f"collections in pgAdmin first, then manually run:")
    print(f"  UPDATE \"nnp-rag\".nnp_km_database SET vanna_embedding_backend = 'local' WHERE id = '{db_id}';")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/migrate_vanna_to_local_embeddings.py <db_id>")
        sys.exit(1)

    target_db_id = sys.argv[1]
    pool.init_pool()
    try:
        asyncio.run(migrate_database(target_db_id))
    finally:
        pool.close_pool()
