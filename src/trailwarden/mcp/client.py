"""MCP client interfaces and server registry for Trailwarden."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from trailwarden.core.config import Settings
from trailwarden.model.backend import ToolDefinition


class McpServerConfig(BaseModel):
    """Connection details for an external MCP server."""

    name: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


class McpToolCall(BaseModel):
    """A namespaced MCP tool call requested by a diagnostic plugin or model."""

    server: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class McpToolResult(BaseModel):
    """Normalized MCP tool result returned to the agent loop."""

    content: str
    raw: Any | None = None


class McpClient(Protocol):
    """Small interface the runtime needs from an MCP client."""

    async def list_tools(self) -> list[ToolDefinition]:
        """Return tools exposed by one MCP server."""
        ...

    async def call_tool(self, call: McpToolCall) -> McpToolResult:
        """Execute one MCP tool call."""
        ...


def build_server_configs(settings: Settings) -> list[McpServerConfig]:
    """Build known external MCP server configs from settings."""
    return [
        McpServerConfig(name="airflow", url=settings.airflow_mcp_url),
        McpServerConfig(name="dbt", url=settings.dbt_mcp_url),
        McpServerConfig(name="trino", url=settings.trino_mcp_url),
        McpServerConfig(name="kubernetes", url=settings.kubernetes_mcp_url),
        McpServerConfig(name="emr", url=settings.emr_mcp_url),
    ]
