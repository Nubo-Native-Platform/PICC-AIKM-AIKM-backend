"""Repository for nnp_km_query_history (NEW)."""

from typing import Dict, List

from src.db.pool import get_cursor


def save(user_id: str, entry: Dict) -> Dict:
    """Insert a query history record and return the created row."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO nnp_km_query_history
                (user_id, question, sql_text, db_id, db_name, area, row_count, has_error)
            VALUES (%(user_id)s, %(question)s, %(sql_text)s, %(db_id)s, %(db_name)s,
                    %(area)s, %(row_count)s, %(has_error)s)
            RETURNING *
            """,
            {
                "user_id": user_id,
                "question": entry.get("question"),
                "sql_text": entry.get("sql_text"),
                "db_id": entry.get("db_id"),
                "db_name": entry.get("db_name"),
                "area": entry.get("area"),
                "row_count": entry.get("row_count"),
                "has_error": bool(entry.get("has_error", False)),
            },
        )
        return cur.fetchone()


def get_by_user(user_id: str, limit: int = 30) -> List[Dict]:
    """Return the most recent history rows for a user, newest first."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM nnp_km_query_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return cur.fetchall()
