"""Command-line interface for Trailwarden."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from trailwarden.agent.runtime import AgentRuntime
from trailwarden.core.contracts import TrailwardenResponse

app = typer.Typer(
    name="trailwarden",
    help="Diagnose failed data pipeline incidents.",
    add_completion=False,
    no_args_is_help=False,
)
console = Console()


@app.command()
def diagnose(
    incident: str | None = typer.Argument(None, help="Incident or failed run description"),
    run_id: str | None = typer.Option(None, "--run-id", help="Orchestrator run id"),
    dag_id: str | None = typer.Option(None, "--dag-id", help="Airflow DAG id"),
    task_id: str | None = typer.Option(None, "--task-id", help="Orchestrator task id"),
    environment: str | None = typer.Option(None, "--environment", "-e", help="Runtime environment"),
    trace_id: str | None = typer.Option(None, "--trace-id", help="Trace id to attach to the run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show trace metadata."),
) -> None:
    """Diagnose a pipeline incident, or open an interactive shell."""
    if incident is None:
        _run_shell()
        return

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

    _render_response(response, verbose=verbose)


def _run_shell() -> None:
    """Run a simple REPL for iterative incident diagnosis."""
    runtime = AgentRuntime()
    verbose = False
    console.print(Panel("Trailwarden shell. Type /help for commands.", border_style="green"))

    while True:
        try:
            incident = console.input("[bold green]trailwarden>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not incident:
            continue
        if incident in {"/exit", "/quit"}:
            break
        if incident == "/help":
            console.print("Enter an incident to diagnose, /verbose to toggle metadata, or /exit.")
            continue
        if incident == "/verbose":
            verbose = not verbose
            state = "on" if verbose else "off"
            console.print(f"[dim]verbose {state}[/dim]")
            continue

        response = asyncio.run(runtime.diagnose(incident))
        _render_response(response, verbose=verbose)


def _render_response(response: TrailwardenResponse, *, verbose: bool = False) -> None:
    """Render a Trailwarden response to the terminal."""
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
