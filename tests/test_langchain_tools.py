"""Tests for LangChain tool definitions."""

from langchain_core.tools import BaseTool

from mcp_postgres.langchain_tools import TOOLS


EXPECTED_NAMES = {
    "pg_query",
    "pg_query_one",
    "pg_list_tables",
    "pg_describe_table",
    "pg_list_schemas",
    "pg_get_table_size",
    "pg_get_indexes",
    "pg_create_table",
    "pg_drop_table",
    "pg_add_column",
    "pg_create_index",
    "pg_insert_row",
    "pg_update_rows",
    "pg_delete_rows",
    "pg_database_size",
    "pg_active_connections",
    "pg_vacuum",
}


def test_tools_count():
    assert len(TOOLS) == 17


def test_all_are_base_tool_instances():
    for t in TOOLS:
        assert isinstance(t, BaseTool), f"{t.name} is not a BaseTool"


def test_all_start_with_pg_prefix():
    for t in TOOLS:
        assert t.name.startswith("pg_"), f"{t.name} missing pg_ prefix"


def test_names_are_unique():
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names)), f"Duplicate names: {names}"


def test_expected_names_match():
    actual = {t.name for t in TOOLS}
    assert actual == EXPECTED_NAMES, f"Mismatch: extra={actual - EXPECTED_NAMES}, missing={EXPECTED_NAMES - actual}"


def test_all_have_descriptions():
    for t in TOOLS:
        assert t.description, f"{t.name} has no description"
