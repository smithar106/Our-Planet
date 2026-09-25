"""Read-only SQL tool for the agent and chat.

The agent and the chatbot may investigate data with SQL, but only through a
tightly-constrained path:

- single statement only (no ``;``)
- must start with SELECT or WITH
- a blocklist rejects mutation / DDL / DCL / COPY / EXPLAIN keywords
- execution happens inside a READ ONLY transaction (Postgres) or ``query_only``
  (SQLite), so even a bypassed validation cannot write
- results are capped

This is a DATA tool, not a general SQL console.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from app.db import get_engine

MAX_ROWS = 100
DEFAULT_LIMIT = 50

_FORBIDDEN: tuple[str, ...] = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "CALL",
    "COPY",
    "VACUUM",
    "ANALYZE",
    "REINDEX",
    "CLUSTER",
    "SET",
    "RESET",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "LOCK",
    "REFRESH",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "EXPLAIN",
    "INTO",
    "REPLACE",
    "DO",
    "PREPARE",
    "DEALLOCATE",
    "LISTEN",
    "NOTIFY",
    "UNLISTEN",
)


def validate_read_only_sql(query: str) -> str | None:
    """Return an error message if the query is unsafe, else None."""
    q = (query or "").strip()
    if not q:
        return "empty query"
    if ";" in q:
        return "multiple statements are not allowed"
    if re.search(r"(--|/\*)", q):
        return "comments are not allowed"
    first_word = re.split(r"\s+", q, maxsplit=1)[0].lower()
    if first_word not in ("select", "with"):
        return "only SELECT or WITH queries are allowed"
    upper = q.upper()
    for word in _FORBIDDEN:
        if re.search(rf"\b{word}\b", upper):
            return f"forbidden keyword: {word}"
    return None


def _apply_limit(query: str, limit: int) -> str:
    q = query.strip().rstrip(";")
    if re.search(r"\blimit\b", q.lower()):
        return q
    return f"{q} LIMIT {int(limit)}"


async def run_sql_query(session: Any, query: str, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    """Execute a validated read-only SQL query. `session` is accepted for tool
    interface consistency but a dedicated read-only connection is used."""
    del session  # use a fresh read-only connection instead

    error = validate_read_only_sql(query)
    if error:
        return {"error": error}

    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_ROWS))
    limited = _apply_limit(query, limit)

    engine = get_engine()
    dialect = engine.dialect.name
    try:
        async with engine.connect() as conn:
            if dialect == "postgresql":
                # Transaction-scoped: auto-resets on commit/rollback.
                await conn.execute(text("SET TRANSACTION READ ONLY"))
                result = await conn.execute(text(limited))
            elif dialect == "sqlite":
                # Connection-scoped: must reset so the pool is not poisoned.
                await conn.execute(text("PRAGMA query_only = ON"))
                try:
                    result = await conn.execute(text(limited))
                finally:
                    await conn.execute(text("PRAGMA query_only = OFF"))
            else:  # pragma: no cover - unknown dialect
                result = await conn.execute(text(limited))
            rows = result.fetchall()
            columns = list(result.keys())
    except Exception as exc:  # pragma: no cover - defensive
        return {"error": f"query failed: {exc}"}

    return {
        "columns": columns,
        "rows": [dict(zip(columns, row, strict=True)) for row in rows],
        "count": len(rows),
        "truncated": len(rows) == limit,
    }
