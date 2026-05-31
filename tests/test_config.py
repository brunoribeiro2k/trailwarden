"""Tests for settings and MCP server config helpers."""

from __future__ import annotations

from trailwarden.core.config import Settings
from trailwarden.mcp.client import build_server_configs


def test_settings_defaults() -> None:
    """Settings expose default placeholder MCP endpoints."""
    settings = Settings()

    assert settings.airflow_mcp_url == "http://localhost:8091/mcp"
    assert settings.dbt_mcp_url == "http://localhost:8092/mcp"
    assert settings.trino_mcp_url == "http://localhost:8082/mcp"
    assert settings.kubernetes_mcp_url == "http://localhost:8093/mcp"
    assert settings.emr_mcp_url == "http://localhost:8094/mcp"
    assert settings.prompt_path.as_posix() == "prompts/trailwarden-system.md"
    assert settings.trace_dir.as_posix() == ".trailwarden/traces"


def test_build_server_configs_includes_all_placeholder_systems() -> None:
    """Server config construction keeps external systems behind the MCP boundary."""
    settings = Settings()

    configs = build_server_configs(settings)
    config_by_name = {config.name: config for config in configs}

    assert set(config_by_name) == {"airflow", "dbt", "trino", "kubernetes", "emr"}
    assert config_by_name["airflow"].url == settings.airflow_mcp_url
    assert config_by_name["emr"].url == settings.emr_mcp_url
