"""Data manipulation operations — insert, update, delete."""

from __future__ import annotations

from ..client import PostgresClient


def insert_row(
    client: PostgresClient,
    table_name: str,
    data: dict,
    schema: str = "public",
) -> dict:
    """Insert a row into a table."""
    full_name = f"{schema}.{table_name}"
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    values = tuple(data.values())

    row = client.fetch_one(
        f"INSERT INTO {full_name} ({columns}) VALUES ({placeholders}) RETURNING *",
        values,
    )
    return {"status": "inserted", "row": row}


def update_rows(
    client: PostgresClient,
    table_name: str,
    data: dict,
    where: str,
    schema: str = "public",
) -> dict:
    """Update rows in a table."""
    full_name = f"{schema}.{table_name}"
    set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
    values = tuple(data.values())

    result = client.execute(
        f"UPDATE {full_name} SET {set_clause} WHERE {where}",
        values,
    )
    return {"status": "updated", "result": result}


def delete_rows(
    client: PostgresClient,
    table_name: str,
    where: str,
    schema: str = "public",
) -> dict:
    """Delete rows from a table."""
    full_name = f"{schema}.{table_name}"
    result = client.execute(f"DELETE FROM {full_name} WHERE {where}")
    return {"status": "deleted", "result": result}
