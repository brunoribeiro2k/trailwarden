"""Tests for the Trailwarden CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from trailwarden import cli
from trailwarden.core.contracts import TrailwardenResponse

runner = CliRunner()


class FakeRuntime:
    """Runtime fake that records diagnose calls made by CLI commands."""

    calls: list[dict[str, object]] = []

    async def diagnose(
        self,
        incident_text: str,
        *,
        run_id: str | None = None,
        dag_id: str | None = None,
        task_id: str | None = None,
        environment: str | None = None,
        trace_id: str | None = None,
    ) -> TrailwardenResponse:
        self.calls.append(
            {
                "incident_text": incident_text,
                "run_id": run_id,
                "dag_id": dag_id,
                "task_id": task_id,
                "environment": environment,
                "trace_id": trace_id,
            }
        )
        return TrailwardenResponse(
            status="needs_more_context",
            answer=f"fake diagnosis for {incident_text}",
            systems_checked=["airflow"],
            trace_id="test-trace",
        )


def test_root_command_runs_one_shot_diagnosis(monkeypatch) -> None:
    """The legacy `trailwarden "incident"` style still works."""
    FakeRuntime.calls = []
    monkeypatch.setattr(cli, "AgentRuntime", FakeRuntime)

    result = runner.invoke(cli.app, ["--dag-id", "orders", "Airflow DAG failed"])

    assert result.exit_code == 0
    assert "fake diagnosis for Airflow DAG failed" in result.output
    assert FakeRuntime.calls == [
        {
            "incident_text": "Airflow DAG failed",
            "run_id": None,
            "dag_id": "orders",
            "task_id": None,
            "environment": None,
            "trace_id": None,
        }
    ]


def test_no_args_runs_interactive_diagnosis(monkeypatch) -> None:
    """Plain `trailwarden` diagnoses each entered incident until exit."""
    FakeRuntime.calls = []
    monkeypatch.setattr(cli, "AgentRuntime", FakeRuntime)

    result = runner.invoke(cli.app, [], input="Airflow DAG failed\n/exit\n")

    assert result.exit_code == 0
    assert "Trailwarden shell" in result.output
    assert "fake diagnosis for Airflow DAG failed" in result.output
    assert FakeRuntime.calls[0]["incident_text"] == "Airflow DAG failed"


def test_shell_can_exit_without_diagnosing(monkeypatch) -> None:
    """Running plain `trailwarden` starts the interactive shell."""
    FakeRuntime.calls = []
    monkeypatch.setattr(cli, "AgentRuntime", FakeRuntime)

    result = runner.invoke(cli.app, [], input="/exit\n")

    assert result.exit_code == 0
    assert "Trailwarden shell" in result.output
    assert FakeRuntime.calls == []
