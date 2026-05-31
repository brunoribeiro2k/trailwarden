"""Diagnostic plugin contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel

from trailwarden.core.contracts import EvidenceItem, RootCause, TrailwardenRequest
from trailwarden.mcp.client import McpClient


class DiagnosticContext(BaseModel):
    """Context shared by diagnostic plugins during one run."""

    request: TrailwardenRequest


class DiagnosticPlugin(Protocol):
    """Protocol every system-specific diagnostic plugin must implement."""

    name: str
    supported_systems: tuple[str, ...]

    def can_handle(self, context: DiagnosticContext) -> bool:
        """Return whether this plugin should inspect the incident."""
        ...

    async def collect_evidence(
        self,
        context: DiagnosticContext,
        mcp_clients: Mapping[str, McpClient],
    ) -> list[EvidenceItem]:
        """Collect evidence from the plugin's systems through MCP clients."""
        ...

    def interpret(self, evidence: list[EvidenceItem]) -> RootCause | None:
        """Interpret collected evidence and return a supported root cause if known."""
        ...


class KeywordDiagnosticPlugin:
    """Small base class for placeholder plugins selected by incident keywords."""

    name: str
    supported_systems: tuple[str, ...]
    keywords: tuple[str, ...]

    def can_handle(self, context: DiagnosticContext) -> bool:
        """Match explicitly supplied identifiers or incident text keywords."""
        text = " ".join(
            value
            for value in [
                context.request.incident_text,
                context.request.dag_id or "",
                context.request.task_id or "",
                context.request.run_id or "",
            ]
            if value
        ).lower()
        return any(keyword in text for keyword in self.keywords)

    async def collect_evidence(
        self,
        context: DiagnosticContext,
        mcp_clients: Mapping[str, McpClient],
    ) -> list[EvidenceItem]:
        """Return placeholder evidence until a live MCP integration is wired."""
        del context, mcp_clients
        system = self.supported_systems[0]
        return [
            EvidenceItem(
                source_system=system,
                identifier=f"{system}:placeholder",
                severity="info",
                message=(
                    f"{system} diagnostic plugin selected, but live MCP evidence "
                    "collection is not wired in Phase 1."
                ),
                raw_reference={"phase": "phase-1-placeholder", "mcp_server": system},
            )
        ]

    def interpret(self, evidence: list[EvidenceItem]) -> RootCause | None:
        """Placeholders never claim a production root cause."""
        del evidence
        return None
