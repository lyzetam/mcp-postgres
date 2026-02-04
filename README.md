# mcp-postgres

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PostgreSQL operations as a Python library, LangChain tools, and MCP server.

## Features

- **17 LangChain tools** for use with LangChain/LangGraph agents
- **17 MCP tools** for use with Claude Code and other MCP clients
- **Modular operations layer** usable as a standalone Python library
- Covers **Queries**, **Schema**, **DDL**, **Data**, and **Admin**

### MCP Tools

| Category | Tools |
|----------|-------|
| Query | `run_query`, `run_query_one` |
| Schema | `list_tables`, `describe_table`, `list_schemas`, `get_table_size`, `get_indexes` |
| DDL | `create_table`, `drop_table`, `add_column`, `create_index` |
| Data | `insert_row`, `update_rows`, `delete_rows` |
| Admin | `get_database_size`, `get_active_connections`, `vacuum_table` |

### LangChain Tools

| Category | Tools |
|----------|-------|
| Query | `pg_query`, `pg_query_one` |
| Schema | `pg_list_tables`, `pg_describe_table`, `pg_list_schemas`, `pg_get_table_size`, `pg_get_indexes` |
| DDL | `pg_create_table`, `pg_drop_table`, `pg_add_column`, `pg_create_index` |
| Data | `pg_insert_row`, `pg_update_rows`, `pg_delete_rows` |
| Admin | `pg_database_size`, `pg_active_connections`, `pg_vacuum` |

## Installation

```bash
# Core library only (psycopg2)
pip install .

# With MCP server support (asyncpg)
pip install ".[mcp]"

# With LangChain tools
pip install ".[langchain]"

# Everything
pip install ".[all]"
```

## Configuration

All settings are read from environment variables with the `POSTGRES_` prefix, or from a `.env` file.
`POSTGRES_URL` takes priority over individual connection parameters.

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_URL` | Full PostgreSQL DSN (takes priority) | `""` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DATABASE` | Database name | `personal` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `""` |

## Quick Start

### As a Python library

```python
from mcp_postgres.client import PostgresClient
from mcp_postgres.operations import query, schema

client = PostgresClient()
tables = schema.list_tables(client, "public")
result = query.run_query(client, "SELECT * FROM users LIMIT 10")
```

### As LangChain tools

```python
from mcp_postgres.langchain_tools import TOOLS

# Use with a LangChain agent
agent = create_react_agent(llm, TOOLS)
```

### As an MCP server

```bash
mcp-postgres
```

### `.env` example

```env
POSTGRES_URL=postgresql://postgres:password@localhost:5432/mydb
# Or use individual parameters:
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DATABASE=personal
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=secret
```

## License

MIT
