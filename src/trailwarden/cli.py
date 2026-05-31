"""Command-line interface for Trailwarden."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from trailwarden.agent.runtime import AgentRuntime

app = typer.Typer(
    name="trailwarden",
    help="Diagnose failed data pipeline incidents.",
    add_completion=False,
)
console = Console()


@app.command()
def diagnose(
    incident: str = typer.Argument(..., help="Incident or failed run description"),
    run_id: str | None = typer.Option(None, "--run-id", help="Orchestrator run id"),
    dag_id: str | None = typer.Option(None, "--dag-id", help="Airflow DAG id"),
    task_id: str | None = typer.Option(None, "--task-id", help="Orchestrator task id"),
    environment: str | None = typer.Option(None, "--environment", "-e", help="Runtime environment"),
    trace_id: str | None = typer.Option(None, "--trace-id", help="Trace id to attach to the run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show trace metadata."),
) -> None:
    """Diagnose a pipeline incident."""
    runtime = AgentRuntime()
    response = asyncio.run(
        runtime.diagnose(
            incident,
            run_id=run_id,
            dag_id=dag_id,
            task_id=task_id,
            environment=environment,
            trace_id=trace_id,
        )
    )

    console.print(Panel(Markdown(response.answer), title="[bold]Trailwarden", border_style="green"))
    if response.root_cause is not None:
        console.print(f"[bold]Root cause:[/bold] {response.root_cause.summary}")
        console.print(f"[dim]confidence: {response.root_cause.confidence:.2f}[/dim]")
    if response.suggested_fixes:
        fix = response.suggested_fixes[0]
        console.print(f"[bold]Suggested fix:[/bold] {fix.title}")
        console.print(fix.description)
    if verbose:
        console.print(f"[dim]status: {response.status}[/dim]")
        systems_checked = ", ".join(response.systems_checked) or "none"
        console.print(f"[dim]systems_checked: {systems_checked}[/dim]")
        console.print(f"[dim]trace: {response.trace_id}[/dim]")


if __name__ == "__main__":
    app()
