"""Tests for diagnostic plugin contracts and placeholder behavior."""

from __future__ import annotations

import pytest

from trailwarden.core.contracts import EvidenceItem, RootCause, TrailwardenRequest
from trailwarden.diagnostics.airflow import AirflowDiagnosticPlugin
from trailwarden.diagnostics.base import DiagnosticContext


def test_airflow_plugin_matches_airflow_incident() -> None:
    """Airflow plugin selects incidents that mention Airflow DAGs."""
    plugin = AirflowDiagnosticPlugin()
    context = DiagnosticContext(
        request=TrailwardenRequest(incident_text="Airflow DAG customer_orders failed")
    )

    assert plugin.can_handle(context)


@pytest.mark.asyncio
async def test_placeholder_plugin_collects_interface_evidence() -> None:
    """Placeholder plugins return evidence without requiring live MCP clients."""
    plugin = AirflowDiagnosticPlugin()
    context = DiagnosticContext(
        request=TrailwardenRequest(incident_text="Airflow DAG customer_orders failed")
    )

    evidence = await plugin.collect_evidence(context, {})

    assert evidence[0].source_system == "airflow"
    assert "not wired" in evidence[0].message
    assert plugin.interpret(evidence) is None


class SampleDiagnosticPlugin:
    """Minimal concrete plugin used to validate the protocol shape."""

    name = "sample"
    supported_systems = ("sample",)

    def can_handle(self, context: DiagnosticContext) -> bool:
        return "sample" in context.request.incident_text

    async def collect_evidence(
        self,
        context: DiagnosticContext,
        mcp_clients: object,
    ) -> list[EvidenceItem]:
        del context, mcp_clients
        return [
            EvidenceItem(
                source_system="sample",
                identifier="sample:1",
                severity="error",
                message="Confirmed failure marker",
            )
        ]

    def interpret(self, evidence: list[EvidenceItem]) -> RootCause | None:
        return RootCause(
            category="sample_failure",
            summary="Sample failure was confirmed",
            confidence=0.9,
            supporting_evidence=evidence,
        )


@pytest.mark.asyncio
async def test_sample_plugin_behavior() -> None:
    """The diagnostic interface supports real plugins returning root causes."""
    plugin = SampleDiagnosticPlugin()
    context = DiagnosticContext(request=TrailwardenRequest(incident_text="sample incident"))

    evidence = await plugin.collect_evidence(context, {})
    root_cause = plugin.interpret(evidence)

    assert plugin.can_handle(context)
    assert root_cause is not None
    assert root_cause.category == "sample_failure"
