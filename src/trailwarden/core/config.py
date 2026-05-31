"""Runtime settings for Trailwarden."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from `TRAILWARDEN_*` environment variables and `.env`."""

    airflow_mcp_url: str = "http://localhost:8091/mcp"
    dbt_mcp_url: str = "http://localhost:8092/mcp"
    trino_mcp_url: str = "http://localhost:8082/mcp"
    kubernetes_mcp_url: str = "http://localhost:8093/mcp"
    emr_mcp_url: str = "http://localhost:8094/mcp"

    llm_profile: str = "local-qwen"
    llm_config_path: Path = Path("config/model-profiles.yaml")

    prompt_path: Path = Path("prompts/trailwarden-system.md")
    trace_dir: Path = Path(".trailwarden/traces")
    max_diagnostic_steps: int = Field(default=12, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRAILWARDEN_",
        extra="ignore",
    )
