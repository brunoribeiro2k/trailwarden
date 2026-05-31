"""Evaluation harness skeleton for Trailwarden.

Usage:
    uv run python evals/run_eval.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trailwarden.agent.runtime import AgentRuntime
from trailwarden.core.contracts import EvalIncident, TrailwardenResponse

console = Console()


def load_incidents(path: Path) -> list[EvalIncident]:
    """Load benchmark incidents from YAML."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return [EvalIncident(**item) for item in data.get("incidents", [])]


def score(response: TrailwardenResponse | Exception, incident: EvalIncident) -> dict[str, str]:
    """Score one response across the planned diagnostic layers."""
    if isinstance(response, Exception):
        return {
            "routing": "fail",
            "evidence": "fail",
            "root_cause": "fail",
            "safety": "fail",
        }

    routed = all(system in response.systems_checked for system in incident.expected_systems)
    status_ok = incident.expected_status is None or response.status == incident.expected_status
    root_cause_ok = (
        incident.expected_root_cause_category is None
        or response.root_cause is not None
        and response.root_cause.category == incident.expected_root_cause_category
    )

    return {
        "routing": "pass" if routed and status_ok else "fail",
        "evidence": "pending",
        "root_cause": "pass" if root_cause_ok else "fail",
        "safety": "pass" if response.status != "diagnosed" or response.suggested_fixes else "fail",
    }


async def run_eval() -> None:
    """Run all benchmark incidents and print layered skeleton scores."""
    incidents = load_incidents(Path(__file__).parent / "incidents.yaml")
    runtime = AgentRuntime()
    rows: list[dict[str, Any]] = []

    for incident in incidents:
        try:
            response: TrailwardenResponse | Exception = await runtime.diagnose(
                incident.incident_text
            )
        except Exception as exc:  # noqa: BLE001
            response = exc
        rows.append({"id": incident.id, **score(response, incident)})

    table = Table(title="Trailwarden Eval Skeleton")
    table.add_column("ID", style="dim")
    table.add_column("Routing")
    table.add_column("Evidence")
    table.add_column("Root Cause")
    table.add_column("Safety")

    for row in rows:
        table.add_row(
            row["id"],
            row["routing"],
            row["evidence"],
            row["root_cause"],
            row["safety"],
        )

    console.print(table)
    console.print(
        "\n[dim]Evidence and root-cause scoring become meaningful after live MCP "
        "clients and model adapters are wired.[/dim]"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()
    asyncio.run(run_eval())
