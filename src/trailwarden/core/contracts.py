"""Public contracts for Trailwarden requests, responses, and traces."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

RunStatus = Literal[
    "diagnosed",
    "needs_more_context",
    "no_failure_found",
    "unsupported_system",
    "failed",
]

Severity = Literal["debug", "info", "warning", "error", "critical", "unknown"]
FixRisk = Literal["low", "medium", "high", "unknown"]


class TimeWindow(BaseModel):
    """Optional incident time window."""

    start: datetime | None = None
    end: datetime | None = None


class TrailwardenRequest(BaseModel):
    """A failed pipeline incident submitted to Trailwarden."""

    incident_text: str
    run_id: str | None = None
    dag_id: str | None = None
    task_id: str | None = None
    time_window: TimeWindow | None = None
    environment: str | None = None
    trace_id: str = Field(default_factory=lambda: uuid4().hex)


class EvidenceItem(BaseModel):
    """One cited observation from an orchestration or runtime system."""

    source_system: str
    identifier: str
    timestamp: datetime | None = None
    severity: Severity = "unknown"
    message: str
    raw_reference: str | dict[str, Any] | None = None


class DiagnosticStep(BaseModel):
    """A diagnostic action taken against one system."""

    system_checked: str
    action_taken: str
    evidence_found: list[EvidenceItem] = Field(default_factory=list)
    conclusion: str


class RootCause(BaseModel):
    """A supported root-cause conclusion."""

    category: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)


class SuggestedFix(BaseModel):
    """A recommended fix and how to verify it."""

    title: str
    description: str
    risk: FixRisk = "unknown"
    verification_step: str


class McpToolCallTrace(BaseModel):
    """A single MCP tool call made during a diagnostic run."""

    server: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None
    latency_ms: float | None = None
    error: str | None = None


class TrailwardenTrace(BaseModel):
    """Debug record for one Trailwarden run."""

    trace_id: str
    request: TrailwardenRequest
    backend: str
    model: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    diagnostic_steps: list[DiagnosticStep] = Field(default_factory=list)
    mcp_tool_calls: list[McpToolCallTrace] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    root_cause: RootCause | None = None
    suggested_fixes: list[SuggestedFix] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class TrailwardenResponse(BaseModel):
    """Structured response returned by Trailwarden."""

    status: RunStatus
    answer: str
    root_cause: RootCause | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    suggested_fixes: list[SuggestedFix] = Field(default_factory=list)
    systems_checked: list[str] = Field(default_factory=list)
    trace_id: str


class EvalIncident(BaseModel):
    """One benchmark incident and its expected diagnostic behavior."""

    id: str
    incident_text: str
    expected_systems: list[str] = Field(default_factory=list)
    expected_status: RunStatus | None = None
    expected_root_cause_category: str | None = None
    notes: str = ""
