"""Tests for operations modules using mocked PostgresClient."""

from unittest.mock import MagicMock

from mcp_postgres.operations import query, schema, ddl, data, admin


def _mock_client(**overrides) -> MagicMock:
    """Create a MagicMock PostgresClient with sensible defaults."""
    client = MagicMock()
    client.fetch_all.return_value = []
    client.fetch_one.return_value = None
    client.execute.return_value = "OK"
    client.dsn = ""
    client.host = "localhost"
    client.port = 5432
    client.database = "test"
    client.user = "postgres"
    client.password = ""
    for k, v in overrides.items():
        setattr(client, k, v)
    return client


# ── Query operations ─────────────────────────────────────────────


class TestRunQuery:
    def test_select_returns_rows(self):
        client = _mock_client()
        client.fetch_all.return_value = [{"id": 1, "name": "a"}]

        result = query.run_query(client, "SELECT * FROM users")

        client.fetch_all.assert_called_once()
        assert result["count"] == 1
        assert result["rows"] == [{"id": 1, "name": "a"}]

    def test_non_select_returns_status(self):
        client = _mock_client()
        client.execute.return_value = "INSERT 0 1"

        result = query.run_query(client, "INSERT INTO users (name) VALUES ('x')")

        client.execute.assert_called_once()
        assert result["status"] == "executed"
        assert result["result"] == "INSERT 0 1"

    def test_with_params(self):
        client = _mock_client()
        client.fetch_all.return_value = [{"id": 1}]

        result = query.run_query(client, "SELECT * FROM users WHERE id = %s", [1])

        client.fetch_all.assert_called_once_with(
            "SELECT * FROM users WHERE id = %s", (1,)
        )
        assert result["count"] == 1


class TestRunQueryOne:
    def test_returns_single_row(self):
        client = _mock_client()
        client.fetch_one.return_value = {"id": 1, "name": "a"}

        result = query.run_query_one(client, "SELECT * FROM users LIMIT 1")

        assert result == {"id": 1, "name": "a"}

    def test_returns_none_when_empty(self):
        client = _mock_client()
        client.fetch_one.return_value = None

        result = query.run_query_one(client, "SELECT * FROM users WHERE id = 999")

        assert result is None


# ── Schema operations ────────────────────────────────────────────


class TestListTables:
    def test_returns_table_list(self):
        client = _mock_client()
        client.fetch_all.return_value = [
            {"table_name": "users", "table_type": "BASE TABLE"},
            {"table_name": "posts", "table_type": "BASE TABLE"},
        ]

        result = schema.list_tables(client, "public")

        assert len(result) == 2
        assert result[0]["table_name"] == "users"


class TestDescribeTable:
    def test_returns_column_info(self):
        client = _mock_client()
        client.fetch_all.return_value = [
            {
                "column_name": "id",
                "data_type": "integer",
                "character_maximum_length": None,
                "is_nullable": "NO",
                "column_default": "nextval('users_id_seq')",
            }
        ]

        result = schema.describe_table(client, "users")

        assert len(result) == 1
        assert result[0]["column"] == "id"
        assert result[0]["nullable"] is False


class TestListSchemas:
    def test_returns_schema_names(self):
        client = _mock_client()
        client.fetch_all.return_value = [
            {"schema_name": "public"},
            {"schema_name": "app"},
        ]

        result = schema.list_schemas(client)

        assert result == ["public", "app"]


# ── DDL operations ───────────────────────────────────────────────


class TestCreateTable:
    def test_creates_table(self):
        client = _mock_client()
        cols = [{"name": "id", "type": "SERIAL PRIMARY KEY"}]

        result = ddl.create_table(client, "test_tbl", cols)

        client.execute.assert_called_once()
        assert result["status"] == "created"
        assert result["table"] == "public.test_tbl"


class TestDropTable:
    def test_drops_table(self):
        client = _mock_client()

        result = ddl.drop_table(client, "test_tbl")

        client.execute.assert_called_once()
        assert result["status"] == "dropped"


# ── Data operations ──────────────────────────────────────────────


class TestInsertRow:
    def test_inserts_and_returns_row(self):
        client = _mock_client()
        client.fetch_one.return_value = {"id": 1, "name": "alice"}

        result = data.insert_row(client, "users", {"name": "alice"})

        client.fetch_one.assert_called_once()
        assert result["status"] == "inserted"
        assert result["row"]["name"] == "alice"


class TestUpdateRows:
    def test_updates_rows(self):
        client = _mock_client()
        client.execute.return_value = "UPDATE 3"

        result = data.update_rows(client, "users", {"active": True}, "id > 0")

        client.execute.assert_called_once()
        assert result["status"] == "updated"
        assert result["result"] == "UPDATE 3"
