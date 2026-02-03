"""Pydantic Settings configuration for mcp-postgres."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PostgreSQL configuration from environment variables or .env file.

    All fields map to POSTGRES_<FIELD_NAME> environment variables.
    POSTGRES_URL takes priority over individual connection parameters.
    """

    url: str = Field(default="", description="Full PostgreSQL DSN (takes priority)")
    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="personal", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="", description="Database password")

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Get configuration from environment variables or .env file."""
    return Settings()
