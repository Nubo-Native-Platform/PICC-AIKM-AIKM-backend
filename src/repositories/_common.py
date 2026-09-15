"""Shared repository helpers (NEW)."""

from typing import Dict, Set, Tuple


def build_set_clause(data: Dict, allowed: Set[str]) -> Tuple[str, Dict]:
    """Build a SQL SET clause from the provided (already exclude_unset) fields.

    Only keys in `allowed` are included. Returns (clause, params) where clause
    looks like 'col_a = %(col_a)s, col_b = %(col_b)s'. `updated_by` is added by
    the caller.
    """
    cols = [k for k in data.keys() if k in allowed]
    clause = ", ".join(f"{c} = %({c})s" for c in cols)
    params = {c: data[c] for c in cols}
    return clause, params
