"""Tests for Trailwarden public contracts."""

from __future__ import annotations

from trailwarden.core.contracts import (
    EvidenceItem,
    TrailwardenRequest,
    TrailwardenResponse,
    TrailwardenTrace,
)


def test_request_generates_trace_id() -> None:
    """A request gets a trace id when one is not supplied."""
    request = TrailwardenRequest(incident_text="Airflow DAG customer_orders failed")

    assert request.trace_id


def test_response_defaults_are_isolated_lists() -> None:
    """Response list fields are independent empty lists by default."""
    first = TrailwardenResponse(status="needs_more_context", answer="pending", trace_id="one")
    second = TrailwardenResponse(status="needs_more_context", answer="pending", trace_id="two")

    first.evidence.append(
        EvidenceItem(
            source_system="airflow",
            identifier="dag:customer_orders",
            message="placeholder",
        )
    )

    assert second.evidence == []


def test_trace_defaults_are_isolated_lists() -> None:
    """Trace list fields are independent empty lists by default."""
    request = TrailwardenRequest(incident_text="Trino query failed")
    first = TrailwardenTrace(trace_id="one", request=request, backend="test", model="test")
    second = TrailwardenTrace(trace_id="two", request=request, backend="test", model="test")

    first.errors.append("boom")

    assert second.errors == []
