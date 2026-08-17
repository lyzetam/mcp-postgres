"""Read-only MCP server for the oura health database.

A separate entrypoint from server.py, not a mode flag on it — server.py backs
the `personal` database (notes/tasks/memories) and is meant to read AND
write there; this one backs `oura` and must never be able to write, so the
two stay physically separate rather than sharing a toggle someone could get
wrong.

Two layers keep this read-only:
  1. The database role (oura_readonly, see fako-cluster's
     apps/base/postgres-cluster/oura-readonly-grants-job.yaml) has SELECT
     only — no INSERT/UPDATE/DELETE/DDL grants, and CONNECT to no database
     other than oura. A write attempt fails in Postgres regardless of what
     this file does.
  2. run_query / run_query_one additionally reject anything that isn't a
     SELECT/WITH up front, so a mistaken write attempt fails fast with a
     clear message instead of a raw Postgres permission-denied trace.

Only 7 tools are registered here — the 8 DDL/write tools in server.py
(create_table, drop_table, add_column, create_index, insert_row,
update_rows, delete_rows, vacuum_table) do not exist in this file at all,
so they cannot appear in a client's tool list for this server. Admin/
introspection tools unrelated to reading health data (get_database_size,
get_active_connections) are left out too — this server's scope is "read the
oura data and its schema," not general Postgres administration.

Same POSTGRES_* environment configuration as server.py (POSTGRES_URL takes
priority; otherwise POSTGRES_HOST/PORT/DATABASE/USER/PASSWORD). Point it at
oura via the persistent tunnel (launchd com.zz.postgres-oura-tunnel,
localhost:15432) and the oura_readonly credential.
"""

import os
import json
from typing import Optional
import asyncpg
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("postgres-oura-readonly")

DATABASE_URL = os.environ.get("POSTGRES_URL")
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DATABASE", "oura")
DB_USER = os.environ.get("POSTGRES_USER", "oura_readonly")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        if DATABASE_URL:
            _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        else:
            _pool = await asyncpg.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                min_size=1,
                max_size=5,
            )
    return _pool


def _require_read_only(query: str) -> None:
    stripped = query.strip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        raise ValueError(
            "This server is read-only: only SELECT/WITH queries are allowed. "
            "Got a statement that starts with a different keyword."
        )


# ============== QUERY TOOLS ==============

@mcp.tool()
async def run_query(query: str, params: Optional[str] = None) -> str:
    """Execute a read-only SQL query (SELECT or WITH) and return results.

    Args:
        query: SQL query to execute — must be SELECT or WITH
        params: Optional JSON array of parameters for parameterized queries
    """
    _require_read_only(query)
    pool = await get_pool()
    param_list = json.loads(params) if params else []

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *param_list)
        result = [dict(row) for row in rows]
        return json.dumps({"rows": result, "count": len(result)}, indent=2, default=str)


@mcp.tool()
async def run_query_one(query: str, params: Optional[str] = None) -> str:
    """Execute a read-only SQL query (SELECT or WITH) and return a single row.

    Args:
        query: SQL query to execute — must be SELECT or WITH
        params: Optional JSON array of parameters
    """
    _require_read_only(query)
    pool = await get_pool()
    param_list = json.loads(params) if params else []

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *param_list)
        return json.dumps(dict(row), indent=2, default=str) if row else json.dumps(None)


# ============== SCHEMA TOOLS ==============

@mcp.tool()
async def list_tables(schema: str = "public") -> str:
    """List all tables in a schema.

    Args:
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = $1
            ORDER BY table_name
        """, schema)
        result = [{"table_name": row["table_name"], "type": row["table_type"]} for row in rows]
        return json.dumps(result, indent=2)


@mcp.tool()
async def describe_table(table_name: str, schema: str = "public") -> str:
    """Get column information for a table.

    Args:
        table_name: Name of the table
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """, schema, table_name)
        result = [{
            "column": row["column_name"],
            "type": row["data_type"],
            "max_length": row["character_maximum_length"],
            "nullable": row["is_nullable"] == "YES",
            "default": row["column_default"],
        } for row in rows]
        return json.dumps(result, indent=2)


@mcp.tool()
async def list_schemas() -> str:
    """List all schemas visible to this role.

    oura_readonly has USAGE on `public` only, so this will show `public`
    plus whatever system schemas Postgres always exposes — nothing from
    other databases, since this role can't see their objects at all.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT LIKE 'pg_%'
            AND schema_name != 'information_schema'
            ORDER BY schema_name
        """)
        return json.dumps([row["schema_name"] for row in rows], indent=2)


@mcp.tool()
async def get_table_size(table_name: str, schema: str = "public") -> str:
    """Get size information for a table.

    Args:
        table_name: Name of the table
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                pg_size_pretty(pg_total_relation_size($1)) as total_size,
                pg_size_pretty(pg_table_size($1)) as table_size,
                pg_size_pretty(pg_indexes_size($1)) as index_size,
                (SELECT count(*) FROM """ + full_name + """) as row_count
        """, full_name)
        return json.dumps({
            "total_size": row["total_size"],
            "table_size": row["table_size"],
            "index_size": row["index_size"],
            "row_count": row["row_count"],
        }, indent=2)


@mcp.tool()
async def get_indexes(table_name: str, schema: str = "public") -> str:
    """Get indexes for a table.

    Args:
        table_name: Name of the table
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = $1 AND tablename = $2
        """, schema, table_name)
        result = [{"name": row["indexname"], "definition": row["indexdef"]} for row in rows]
        return json.dumps(result, indent=2)


def main():
    """Entry point for the read-only MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
