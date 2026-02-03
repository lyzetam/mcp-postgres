"""LangChain tool wrappers for PostgreSQL operations."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

import warnings

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, ConfigDict, Field

# Suppress Pydantic warnings about "schema" field shadowing BaseModel.schema()
warnings.filterwarnings("ignore", message='Field name "schema" in .* shadows an attribute')

from .client import PostgresClient
from .operations import query as query_ops
from .operations import schema as schema_ops
from .operations import ddl as ddl_ops
from .operations import data as data_ops
from .operations import admin as admin_ops


@lru_cache
def _get_client() -> PostgresClient:
    """Singleton PostgresClient from environment variables."""
    return PostgresClient()


def _json(obj: object) -> str:
    return json.dumps(obj, indent=2, default=str)


# ── Query tools ──────────────────────────────────────────────────


class QueryArgs(BaseModel):
    query: str = Field(description="SQL query to execute")
    params: Optional[str] = Field(
        default=None,
        description="Optional JSON array of parameters for parameterized queries",
    )


@tool(args_schema=QueryArgs)
def pg_query(query: str, params: Optional[str] = None) -> str:
    """Execute a SQL query and return results. SELECT/WITH returns rows; others return status."""
    param_list = json.loads(params) if params else None
    return _json(query_ops.run_query(_get_client(), query, param_list))


@tool(args_schema=QueryArgs)
def pg_query_one(query: str, params: Optional[str] = None) -> str:
    """Execute a SQL query and return a single row."""
    param_list = json.loads(params) if params else None
    return _json(query_ops.run_query_one(_get_client(), query, param_list))


# ── Schema tools ─────────────────────────────────────────────────


@tool
def pg_list_tables(schema: str = "public") -> str:
    """List all tables in a schema."""
    return _json(schema_ops.list_tables(_get_client(), schema))


class DescribeTableArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=DescribeTableArgs)
def pg_describe_table(table_name: str, schema: str = "public") -> str:
    """Get column information for a table."""
    return _json(schema_ops.describe_table(_get_client(), table_name, schema))


@tool
def pg_list_schemas() -> str:
    """List all schemas in the database."""
    return _json(schema_ops.list_schemas(_get_client()))


class TableSchemaArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=TableSchemaArgs)
def pg_get_table_size(table_name: str, schema: str = "public") -> str:
    """Get size information for a table including row count."""
    return _json(schema_ops.get_table_size(_get_client(), table_name, schema))


@tool(args_schema=TableSchemaArgs)
def pg_get_indexes(table_name: str, schema: str = "public") -> str:
    """Get indexes for a table."""
    return _json(schema_ops.get_indexes(_get_client(), table_name, schema))


# ── DDL tools ────────────────────────────────────────────────────


class CreateTableArgs(BaseModel):
    table_name: str = Field(description="Name for the new table")
    columns: str = Field(
        description=(
            'JSON array of column definitions, e.g. '
            '[{"name": "id", "type": "SERIAL PRIMARY KEY"}, '
            '{"name": "email", "type": "VARCHAR(255) NOT NULL"}]'
        )
    )
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=CreateTableArgs)
def pg_create_table(table_name: str, columns: str, schema: str = "public") -> str:
    """Create a new table. Columns is a JSON string array of {name, type} objects."""
    cols = json.loads(columns)
    return _json(ddl_ops.create_table(_get_client(), table_name, cols, schema))


class DropTableArgs(BaseModel):
    table_name: str = Field(description="Name of the table to drop")
    schema: str = Field(default="public", description="Schema name")
    cascade: bool = Field(default=False, description="Also drop dependent objects")


@tool(args_schema=DropTableArgs)
def pg_drop_table(
    table_name: str, schema: str = "public", cascade: bool = False
) -> str:
    """Drop a table."""
    return _json(ddl_ops.drop_table(_get_client(), table_name, schema, cascade))


class AddColumnArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    column_name: str = Field(description="Name of the new column")
    column_type: str = Field(
        description="Column type definition (e.g. 'VARCHAR(255) NOT NULL')"
    )
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=AddColumnArgs)
def pg_add_column(
    table_name: str,
    column_name: str,
    column_type: str,
    schema: str = "public",
) -> str:
    """Add a column to a table."""
    return _json(
        ddl_ops.add_column(_get_client(), table_name, column_name, column_type, schema)
    )


class CreateIndexArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    columns: str = Field(description="Comma-separated column names to index")
    index_name: Optional[str] = Field(
        default=None, description="Name for the index (auto-generated if not provided)"
    )
    unique: bool = Field(default=False, description="Create a unique index")
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=CreateIndexArgs)
def pg_create_index(
    table_name: str,
    columns: str,
    index_name: Optional[str] = None,
    unique: bool = False,
    schema: str = "public",
) -> str:
    """Create an index on a table."""
    return _json(
        ddl_ops.create_index(
            _get_client(), table_name, columns, index_name, unique, schema
        )
    )


# ── Data tools ───────────────────────────────────────────────────


class InsertRowArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    data: str = Field(
        description="JSON object with column:value pairs to insert"
    )
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=InsertRowArgs)
def pg_insert_row(table_name: str, data: str, schema: str = "public") -> str:
    """Insert a row into a table. Data is a JSON string of column:value pairs."""
    row_data = json.loads(data)
    return _json(data_ops.insert_row(_get_client(), table_name, row_data, schema))


class UpdateRowsArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    data: str = Field(description="JSON object with column:value pairs to update")
    where: str = Field(description="WHERE clause (without 'WHERE' keyword)")
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=UpdateRowsArgs)
def pg_update_rows(
    table_name: str, data: str, where: str, schema: str = "public"
) -> str:
    """Update rows in a table matching a WHERE clause."""
    row_data = json.loads(data)
    return _json(
        data_ops.update_rows(_get_client(), table_name, row_data, where, schema)
    )


class DeleteRowsArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    where: str = Field(description="WHERE clause (without 'WHERE' keyword)")
    schema: str = Field(default="public", description="Schema name")


@tool(args_schema=DeleteRowsArgs)
def pg_delete_rows(table_name: str, where: str, schema: str = "public") -> str:
    """Delete rows from a table matching a WHERE clause."""
    return _json(data_ops.delete_rows(_get_client(), table_name, where, schema))


# ── Admin tools ──────────────────────────────────────────────────


@tool
def pg_database_size() -> str:
    """Get the total size of the database."""
    return _json(admin_ops.get_database_size(_get_client()))


@tool
def pg_active_connections() -> str:
    """Get active database connections."""
    return _json(admin_ops.get_active_connections(_get_client()))


class VacuumArgs(BaseModel):
    table_name: str = Field(description="Name of the table")
    schema: str = Field(default="public", description="Schema name")
    analyze: bool = Field(
        default=True, description="Also update statistics (default: True)"
    )


@tool(args_schema=VacuumArgs)
def pg_vacuum(
    table_name: str, schema: str = "public", analyze: bool = True
) -> str:
    """Vacuum a table to reclaim space and update statistics."""
    return _json(admin_ops.vacuum_table(_get_client(), table_name, schema, analyze))


# ── Exported list ────────────────────────────────────────────────

TOOLS: list[BaseTool] = [
    pg_query,
    pg_query_one,
    pg_list_tables,
    pg_describe_table,
    pg_list_schemas,
    pg_get_table_size,
    pg_get_indexes,
    pg_create_table,
    pg_drop_table,
    pg_add_column,
    pg_create_index,
    pg_insert_row,
    pg_update_rows,
    pg_delete_rows,
    pg_database_size,
    pg_active_connections,
    pg_vacuum,
]
