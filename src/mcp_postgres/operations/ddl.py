"""DDL operations — create/drop tables, add columns, create indexes."""

from __future__ import annotations

import json

from ..client import PostgresClient


def create_table(
    client: PostgresClient,
    table_name: str,
    columns: list[dict],
    schema: str = "public",
) -> dict:
    """Create a new table. Columns: [{"name": "id", "type": "SERIAL PRIMARY KEY"}, ...]."""
    col_defs = ", ".join([f"{c['name']} {c['type']}" for c in columns])
    full_name = f"{schema}.{table_name}"
    client.execute(f"CREATE TABLE {full_name} ({col_defs})")
    return {"status": "created", "table": full_name, "columns": columns}


def drop_table(
    client: PostgresClient,
    table_name: str,
    schema: str = "public",
    cascade: bool = False,
) -> dict:
    """Drop a table."""
    full_name = f"{schema}.{table_name}"
    cascade_str = "CASCADE" if cascade else ""
    client.execute(f"DROP TABLE {full_name} {cascade_str}")
    return {"status": "dropped", "table": full_name}


def add_column(
    client: PostgresClient,
    table_name: str,
    column_name: str,
    column_type: str,
    schema: str = "public",
) -> dict:
    """Add a column to a table."""
    full_name = f"{schema}.{table_name}"
    client.execute(f"ALTER TABLE {full_name} ADD COLUMN {column_name} {column_type}")
    return {"status": "column_added", "table": full_name, "column": column_name, "type": column_type}


def create_index(
    client: PostgresClient,
    table_name: str,
    columns: str,
    index_name: str | None = None,
    unique: bool = False,
    schema: str = "public",
) -> dict:
    """Create an index on a table."""
    full_name = f"{schema}.{table_name}"
    if not index_name:
        index_name = f"idx_{table_name}_{columns.replace(',', '_').replace(' ', '')}"
    unique_str = "UNIQUE" if unique else ""
    client.execute(f"CREATE {unique_str} INDEX {index_name} ON {full_name} ({columns})")
    return {"status": "index_created", "index_name": index_name, "table": full_name, "columns": columns, "unique": unique}
