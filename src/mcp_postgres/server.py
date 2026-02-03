"""MCP Server for Local PostgreSQL Database.

Provides tools for:
- Running SQL queries
- Schema management
- Table operations
- Data import/export
- Database administration

This is for personal data storage in the local K8s PostgreSQL instance.
Supabase is used for software development projects.
"""

import os
import json
from typing import Optional
import asyncpg
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("postgres")

# Configuration from environment
DATABASE_URL = os.environ.get("POSTGRES_URL")
# Alternative: individual components
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DATABASE", "personal")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")

# Connection pool
_pool = None


async def get_pool():
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        if DATABASE_URL:
            _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        else:
            _pool = await asyncpg.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                min_size=1,
                max_size=10,
            )
    return _pool


# ============== QUERY TOOLS ==============

@mcp.tool()
async def run_query(query: str, params: Optional[str] = None) -> str:
    """Execute a SQL query and return results.

    Args:
        query: SQL query to execute
        params: Optional JSON array of parameters for parameterized queries
    """
    pool = await get_pool()

    param_list = json.loads(params) if params else []

    async with pool.acquire() as conn:
        # Determine if it's a SELECT or modifying query
        query_lower = query.strip().lower()
        if query_lower.startswith("select") or query_lower.startswith("with"):
            rows = await conn.fetch(query, *param_list)
            result = [dict(row) for row in rows]
            return json.dumps({
                "rows": result,
                "count": len(result)
            }, indent=2, default=str)
        else:
            result = await conn.execute(query, *param_list)
            return json.dumps({
                "status": "executed",
                "result": result
            }, indent=2)


@mcp.tool()
async def run_query_one(query: str, params: Optional[str] = None) -> str:
    """Execute a SQL query and return single row.

    Args:
        query: SQL query to execute
        params: Optional JSON array of parameters
    """
    pool = await get_pool()

    param_list = json.loads(params) if params else []

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *param_list)
        if row:
            return json.dumps(dict(row), indent=2, default=str)
        return json.dumps(None)


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
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            ORDER BY ordinal_position
        """, schema, table_name)

        result = []
        for row in rows:
            result.append({
                "column": row["column_name"],
                "type": row["data_type"],
                "max_length": row["character_maximum_length"],
                "nullable": row["is_nullable"] == "YES",
                "default": row["column_default"],
            })

        return json.dumps(result, indent=2)


@mcp.tool()
async def list_schemas() -> str:
    """List all schemas in the database."""
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
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = $1 AND tablename = $2
        """, schema, table_name)

        result = [{"name": row["indexname"], "definition": row["indexdef"]} for row in rows]
        return json.dumps(result, indent=2)


# ============== DDL TOOLS ==============

@mcp.tool()
async def create_table(
    table_name: str,
    columns: str,
    schema: str = "public"
) -> str:
    """Create a new table.

    Args:
        table_name: Name for the new table
        columns: JSON array of column definitions, e.g.:
            [{"name": "id", "type": "SERIAL PRIMARY KEY"},
             {"name": "email", "type": "VARCHAR(255) NOT NULL"},
             {"name": "created_at", "type": "TIMESTAMP DEFAULT NOW()"}]
        schema: Schema name (default: public)
    """
    pool = await get_pool()

    cols = json.loads(columns)
    col_defs = ", ".join([f"{c['name']} {c['type']}" for c in cols])
    full_name = f"{schema}.{table_name}"

    async with pool.acquire() as conn:
        await conn.execute(f"CREATE TABLE {full_name} ({col_defs})")

        return json.dumps({
            "status": "created",
            "table": full_name,
            "columns": cols
        }, indent=2)


@mcp.tool()
async def drop_table(table_name: str, schema: str = "public", cascade: bool = False) -> str:
    """Drop a table.

    Args:
        table_name: Name of the table to drop
        schema: Schema name (default: public)
        cascade: Also drop dependent objects
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"
    cascade_str = "CASCADE" if cascade else ""

    async with pool.acquire() as conn:
        await conn.execute(f"DROP TABLE {full_name} {cascade_str}")

        return json.dumps({
            "status": "dropped",
            "table": full_name
        }, indent=2)


@mcp.tool()
async def add_column(
    table_name: str,
    column_name: str,
    column_type: str,
    schema: str = "public"
) -> str:
    """Add a column to a table.

    Args:
        table_name: Name of the table
        column_name: Name of the new column
        column_type: Column type definition (e.g., 'VARCHAR(255) NOT NULL')
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"

    async with pool.acquire() as conn:
        await conn.execute(f"ALTER TABLE {full_name} ADD COLUMN {column_name} {column_type}")

        return json.dumps({
            "status": "column_added",
            "table": full_name,
            "column": column_name,
            "type": column_type
        }, indent=2)


@mcp.tool()
async def create_index(
    table_name: str,
    columns: str,
    index_name: Optional[str] = None,
    unique: bool = False,
    schema: str = "public"
) -> str:
    """Create an index on a table.

    Args:
        table_name: Name of the table
        columns: Comma-separated column names to index
        index_name: Name for the index (auto-generated if not provided)
        unique: Create a unique index
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"

    if not index_name:
        index_name = f"idx_{table_name}_{columns.replace(',', '_').replace(' ', '')}"

    unique_str = "UNIQUE" if unique else ""

    async with pool.acquire() as conn:
        await conn.execute(f"CREATE {unique_str} INDEX {index_name} ON {full_name} ({columns})")

        return json.dumps({
            "status": "index_created",
            "index_name": index_name,
            "table": full_name,
            "columns": columns,
            "unique": unique
        }, indent=2)


# ============== DATA TOOLS ==============

@mcp.tool()
async def insert_row(
    table_name: str,
    data: str,
    schema: str = "public"
) -> str:
    """Insert a row into a table.

    Args:
        table_name: Name of the table
        data: JSON object with column:value pairs
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"

    row_data = json.loads(data)
    columns = ", ".join(row_data.keys())
    placeholders = ", ".join([f"${i+1}" for i in range(len(row_data))])
    values = list(row_data.values())

    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            f"INSERT INTO {full_name} ({columns}) VALUES ({placeholders}) RETURNING *",
            *values
        )

        return json.dumps({
            "status": "inserted",
            "row": dict(result) if result else None
        }, indent=2, default=str)


@mcp.tool()
async def update_rows(
    table_name: str,
    data: str,
    where: str,
    schema: str = "public"
) -> str:
    """Update rows in a table.

    Args:
        table_name: Name of the table
        data: JSON object with column:value pairs to update
        where: WHERE clause (without 'WHERE' keyword)
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"

    row_data = json.loads(data)
    set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(row_data.keys())])
    values = list(row_data.values())

    async with pool.acquire() as conn:
        result = await conn.execute(
            f"UPDATE {full_name} SET {set_clause} WHERE {where}",
            *values
        )

        return json.dumps({
            "status": "updated",
            "result": result
        }, indent=2)


@mcp.tool()
async def delete_rows(
    table_name: str,
    where: str,
    schema: str = "public"
) -> str:
    """Delete rows from a table.

    Args:
        table_name: Name of the table
        where: WHERE clause (without 'WHERE' keyword)
        schema: Schema name (default: public)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"

    async with pool.acquire() as conn:
        result = await conn.execute(f"DELETE FROM {full_name} WHERE {where}")

        return json.dumps({
            "status": "deleted",
            "result": result
        }, indent=2)


# ============== ADMIN TOOLS ==============

@mcp.tool()
async def get_database_size() -> str:
    """Get the total size of the database."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                pg_database.datname as database_name,
                pg_size_pretty(pg_database_size(pg_database.datname)) as size
            FROM pg_database
            WHERE pg_database.datname = current_database()
        """)

        return json.dumps({
            "database": row["database_name"],
            "size": row["size"]
        }, indent=2)


@mcp.tool()
async def get_active_connections() -> str:
    """Get active database connections."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                pid,
                usename,
                application_name,
                client_addr,
                state,
                query_start,
                query
            FROM pg_stat_activity
            WHERE datname = current_database()
            AND pid != pg_backend_pid()
        """)

        result = []
        for row in rows:
            result.append({
                "pid": row["pid"],
                "user": row["usename"],
                "application": row["application_name"],
                "client": str(row["client_addr"]) if row["client_addr"] else None,
                "state": row["state"],
                "query_start": str(row["query_start"]) if row["query_start"] else None,
                "query": row["query"][:200] if row["query"] else None,
            })

        return json.dumps(result, indent=2)


@mcp.tool()
async def vacuum_table(table_name: str, schema: str = "public", analyze: bool = True) -> str:
    """Vacuum a table to reclaim space and update statistics.

    Args:
        table_name: Name of the table
        schema: Schema name (default: public)
        analyze: Also update statistics (default: True)
    """
    pool = await get_pool()
    full_name = f"{schema}.{table_name}"
    analyze_str = "ANALYZE" if analyze else ""

    async with pool.acquire() as conn:
        # VACUUM cannot run in a transaction
        await conn.execute(f"VACUUM {analyze_str} {full_name}")

        return json.dumps({
            "status": "vacuumed",
            "table": full_name,
            "analyzed": analyze
        }, indent=2)


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
