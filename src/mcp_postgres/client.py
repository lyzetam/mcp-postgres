"""PostgreSQL client with psycopg2 for sync operations."""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


class PostgresClient:
    """Manages psycopg2 connections to PostgreSQL.

    Reads configuration from environment variables:
    - POSTGRES_URL (full DSN, takes priority)
    - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD
    """

    def __init__(
        self,
        dsn: str | None = None,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.dsn = dsn or os.environ.get("POSTGRES_URL", "")
        self.host = host or os.environ.get("POSTGRES_HOST", "localhost")
        self.port = port or int(os.environ.get("POSTGRES_PORT", "5432"))
        self.database = database or os.environ.get("POSTGRES_DATABASE", "personal")
        self.user = user or os.environ.get("POSTGRES_USER", "postgres")
        self.password = password or os.environ.get("POSTGRES_PASSWORD", "")

    def connect(self):
        """Get a new psycopg2 connection."""
        if self.dsn:
            return psycopg2.connect(self.dsn)
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def execute(self, query: str, params: tuple | None = None) -> str:
        """Execute a non-SELECT query, return status string."""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.statusmessage

    def fetch_all(self, query: str, params: tuple | None = None) -> list[dict]:
        """Execute a SELECT query, return list of dicts."""
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def fetch_one(self, query: str, params: tuple | None = None) -> dict | None:
        """Execute a query, return single row as dict or None."""
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
