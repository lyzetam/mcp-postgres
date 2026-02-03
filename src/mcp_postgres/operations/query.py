"""Query execution operations."""

from __future__ import annotations

import json

from ..client import PostgresClient


def run_query(client: PostgresClient, query: str, params: list | None = None) -> dict:
    """Execute a SQL query and return results."""
    query_lower = query.strip().lower()
    if query_lower.startswith("select") or query_lower.startswith("with"):
        rows = client.fetch_all(query, tuple(params) if params else None)
        return {"rows": rows, "count": len(rows)}
    else:
        result = client.execute(query, tuple(params) if params else None)
        return {"status": "executed", "result": result}


def run_query_one(client: PostgresClient, query: str, params: list | None = None) -> dict | None:
    """Execute a SQL query and return single row."""
    return client.fetch_one(query, tuple(params) if params else None)
