"""Tests for the Trailwarden runtime skeleton."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trailwarden.agent.runtime import AgentRuntime
from trailwarden.core.config import Settings
from trailwarden.core.contracts import TrailwardenRequest, TrailwardenTrace
from trailwarden.model.backend import Message, ModelTurn, NotConfiguredBackend, ToolDefinition
from trailwarden.observability.tracing import TraceRecorder


class FakeModelBackend:
    """Small model backend used to verify runtime/backend integration."""

    name = "litellm"
    model = "ollama/qwen2.5:14b"

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
    ) -> ModelTurn:
        del system, messages, tools
        return ModelTurn(content="Local model summary.")


class FakeTriageBackend:
    """Model backend fake that selects diagnostics from conversational text."""

    name = "litellm"
    model = "ollama/qwen2.5:14b"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
    ) -> ModelTurn:
        del system, tools
        content = str(messages[-1].content)
        self.calls.append(content)
        if "choose which supported systems" in content:
            return ModelTurn(content='{"systems":["dbt"]}')
        return ModelTurn(content="The model understood this as a dbt incident.")


def test_load_system_prompt_fallback(tmp_path: Path) -> None:
    """Runtime falls back gracefully when the prompt file is missing."""
    prompt = AgentRuntime._load_system_prompt(tmp_path / "missing.md")

    assert "Trailwarden" in prompt


@pytest.mark.asyncio
async def test_runtime_returns_skeleton_response(tmp_path: Path) -> None:
    """The skeleton runtime returns a clear not-configured response."""
    settings = Settings(
        prompt_path=tmp_path / "missing.md",
        trace_dir=tmp_path / "traces",
    )
    runtime = AgentRuntime(settings=settings, backend=NotConfiguredBackend())

    response = await runtime.diagnose("Airflow DAG customer_orders failed last night")

    assert response.status == "needs_more_context"
    assert "Phase 1 skeleton is ready" in response.answer
    assert response.systems_checked == ["airflow"]
    assert response.trace_id
    assert list((tmp_path / "traces").glob("*.jsonl"))


@pytest.mark.asyncio
async def test_runtime_uses_injected_model_backend(tmp_path: Path) -> None:
    """A swappable model backend can drive the same response contract."""
    settings = Settings(
        prompt_path=tmp_path / "missing.md",
        trace_dir=tmp_path / "traces",
    )
    runtime = AgentRuntime(settings=settings, backend=FakeModelBackend())

    response = await runtime.diagnose("Airflow DAG customer_orders failed last night")

    assert response.status == "needs_more_context"
    assert "Local model summary" in response.answer
    assert response.systems_checked == ["airflow"]
    assert response.trace_id


@pytest.mark.asyncio
async def test_runtime_uses_model_triage_before_keyword_fallback(tmp_path: Path) -> None:
    """Conversational incidents can be routed by the model without keyword parsing."""
    settings = Settings(
        prompt_path=tmp_path / "missing.md",
        trace_dir=tmp_path / "traces",
    )
    backend = FakeTriageBackend()
    runtime = AgentRuntime(settings=settings, backend=backend)

    response = await runtime.diagnose("The customer orders freshness check is broken again")

    assert response.status == "needs_more_context"
    assert response.systems_checked == ["dbt"]
    assert "dbt incident" in response.answer
    assert any("choose which supported systems" in call for call in backend.calls)


@pytest.mark.asyncio
async def test_runtime_returns_unsupported_system_when_no_plugin_matches(tmp_path: Path) -> None:
    """Incidents outside configured plugins get an explicit unsupported response."""
    settings = Settings(
        prompt_path=tmp_path / "missing.md",
        trace_dir=tmp_path / "traces",
    )
    runtime = AgentRuntime(settings=settings, backend=NotConfiguredBackend())

    response = await runtime.diagnose("The nightly spreadsheet export failed")

    assert response.status == "unsupported_system"
    assert response.systems_checked == []


def test_trace_recorder_writes_jsonl(tmp_path: Path) -> None:
    """Trace recorder appends JSON lines with serialized trace data."""
    request = TrailwardenRequest(incident_text="dbt model failed")
    trace = TrailwardenTrace(
        trace_id=request.trace_id,
        request=request,
        backend="test",
        model="test-model",
    )

    path = TraceRecorder(tmp_path).write(trace)

    lines = path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(lines[0])
    assert payload["trace_id"] == request.trace_id
    assert payload["request"]["incident_text"] == "dbt model failed"
    assert payload["finished_at"]
