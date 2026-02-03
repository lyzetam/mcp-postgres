"""Database administration operations."""

from __future__ import annotations

from ..client import PostgresClient


def get_database_size(client: PostgresClient) -> dict:
    """Get the total size of the database."""
    row = client.fetch_one(
        "SELECT pg_database.datname as database_name, "
        "pg_size_pretty(pg_database_size(pg_database.datname)) as size "
        "FROM pg_database WHERE pg_database.datname = current_database()"
    )
    return {"database": row["database_name"], "size": row["size"]} if row else {}


def get_active_connections(client: PostgresClient) -> list[dict]:
    """Get active database connections."""
    rows = client.fetch_all(
        "SELECT pid, usename, application_name, client_addr, state, "
        "query_start, query FROM pg_stat_activity "
        "WHERE datname = current_database() AND pid != pg_backend_pid()"
    )
    return [
        {
            "pid": r["pid"],
            "user": r["usename"],
            "application": r["application_name"],
            "client": str(r["client_addr"]) if r["client_addr"] else None,
            "state": r["state"],
            "query_start": str(r["query_start"]) if r.get("query_start") else None,
            "query": r["query"][:200] if r.get("query") else None,
        }
        for r in rows
    ]


def vacuum_table(
    client: PostgresClient,
    table_name: str,
    schema: str = "public",
    analyze: bool = True,
) -> dict:
    """Vacuum a table to reclaim space and update statistics."""
    full_name = f"{schema}.{table_name}"
    analyze_str = "ANALYZE" if analyze else ""
    # VACUUM cannot run in a transaction, use autocommit connection
    import psycopg2
    if client.dsn:
        conn = psycopg2.connect(client.dsn)
    else:
        conn = psycopg2.connect(
            host=client.host, port=client.port, dbname=client.database,
            user=client.user, password=client.password,
        )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"VACUUM {analyze_str} {full_name}")
    conn.close()
    return {"status": "vacuumed", "table": full_name, "analyzed": analyze}
