"""Schema inspection operations."""

from __future__ import annotations

from ..client import PostgresClient


def list_tables(client: PostgresClient, schema: str = "public") -> list[dict]:
    """List all tables in a schema."""
    return client.fetch_all(
        "SELECT table_name, table_type FROM information_schema.tables "
        "WHERE table_schema = %s ORDER BY table_name",
        (schema,),
    )


def describe_table(client: PostgresClient, table_name: str, schema: str = "public") -> list[dict]:
    """Get column information for a table."""
    rows = client.fetch_all(
        "SELECT column_name, data_type, character_maximum_length, "
        "is_nullable, column_default "
        "FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s "
        "ORDER BY ordinal_position",
        (schema, table_name),
    )
    return [
        {
            "column": r["column_name"],
            "type": r["data_type"],
            "max_length": r["character_maximum_length"],
            "nullable": r["is_nullable"] == "YES",
            "default": r["column_default"],
        }
        for r in rows
    ]


def list_schemas(client: PostgresClient) -> list[str]:
    """List all schemas in the database."""
    rows = client.fetch_all(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name NOT LIKE 'pg_%%' "
        "AND schema_name != 'information_schema' "
        "ORDER BY schema_name"
    )
    return [r["schema_name"] for r in rows]


def get_table_size(client: PostgresClient, table_name: str, schema: str = "public") -> dict:
    """Get size information for a table."""
    full_name = f"{schema}.{table_name}"
    row = client.fetch_one(
        "SELECT pg_size_pretty(pg_total_relation_size(%s)) as total_size, "
        "pg_size_pretty(pg_table_size(%s)) as table_size, "
        "pg_size_pretty(pg_indexes_size(%s)) as index_size",
        (full_name, full_name, full_name),
    )
    count_row = client.fetch_one(f"SELECT count(*) as cnt FROM {full_name}")
    return {
        "total_size": row["total_size"] if row else "N/A",
        "table_size": row["table_size"] if row else "N/A",
        "index_size": row["index_size"] if row else "N/A",
        "row_count": count_row["cnt"] if count_row else 0,
    }


def get_indexes(client: PostgresClient, table_name: str, schema: str = "public") -> list[dict]:
    """Get indexes for a table."""
    rows = client.fetch_all(
        "SELECT indexname, indexdef FROM pg_indexes "
        "WHERE schemaname = %s AND tablename = %s",
        (schema, table_name),
    )
    return [{"name": r["indexname"], "definition": r["indexdef"]} for r in rows]
