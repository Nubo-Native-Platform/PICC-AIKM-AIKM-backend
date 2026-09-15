"""Repository for model_details."""

from typing import Dict, Optional

from src.db.pool import get_cursor


def get_active_text_model(model_type: str) -> Optional[Dict]:
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT "ModelName", "API_Key"
            FROM model_details
            WHERE LOWER("Model_Type") = %s
              AND LOWER("Usage") = 'text'
              AND LOWER("Status") = 'active'
            ORDER BY "ModelName"
            LIMIT 1
            """,
            (model_type,),
        )
        return cur.fetchone()
