"""Trailwarden diagnostic runtime skeleton."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from trailwarden.core.config import Settings
from trailwarden.core.contracts import (
    DiagnosticStep,
    RootCause,
    SuggestedFix,
    TrailwardenRequest,
    TrailwardenResponse,
    TrailwardenTrace,
)
from trailwarden.diagnostics import (
    AirflowDiagnosticPlugin,
    DbtDiagnosticPlugin,
    KubernetesDiagnosticPlugin,
    TrinoDiagnosticPlugin,
)
from trailwarden.diagnostics.base import DiagnosticContext, DiagnosticPlugin
from trailwarden.mcp.client import McpClient
from trailwarden.model.backend import Message, ModelBackend, NotConfiguredBackend
from trailwarden.observability.tracing import TraceRecorder


class AgentRuntime:
    """Coordinate prompt loading, diagnostic plugins, model turns, MCP tools, and traces."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        backend: ModelBackend | None = None,
        mcp_clients: Mapping[str, McpClient] | None = None,
        diagnostic_plugins: Sequence[DiagnosticPlugin] | None = None,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.backend = backend or NotConfiguredBackend()
        self.mcp_clients = dict(mcp_clients or {})
        self.diagnostic_plugins = list(diagnostic_plugins or self._default_plugins())
        self.trace_recorder = trace_recorder or TraceRecorder(self.settings.trace_dir)
        self.system_prompt = self._load_system_prompt(self.settings.prompt_path)

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
        """Diagnose a pipeline incident.

        Phase 1 records the contract and trace shape. Live MCP evidence collection and
        model-backed reasoning are intentionally future work.
        """
        request = TrailwardenRequest(
            incident_text=incident_text,
            run_id=run_id,
            dag_id=dag_id,
            task_id=task_id,
            environment=environment,
            trace_id=trace_id or TrailwardenRequest(incident_text=incident_text).trace_id,
        )
        context = DiagnosticContext(request=request)
        trace = TrailwardenTrace(
            trace_id=request.trace_id,
            request=request,
            backend=self.backend.name,
            model=self.backend.model,
        )

        matching_plugins = [
            plugin for plugin in self.diagnostic_plugins if plugin.can_handle(context)
        ]
        if not matching_plugins:
            trace.errors.append("No diagnostic plugin matched the incident context.")
            turn = self._model_summary(request)
            trace.suggested_fixes.append(self._context_fix())
            self.trace_recorder.write(trace)
            return TrailwardenResponse(
                status="unsupported_system",
                answer=(
                    f"{turn} No supported diagnostic plugin matched this incident. "
                    "Add a system name, DAG/task/run id, query id, pod id, or "
                    "configure a new plugin."
                ),
                suggested_fixes=trace.suggested_fixes,
                trace_id=request.trace_id,
            )

        root_cause: RootCause | None = None
        for plugin in matching_plugins[: self.settings.max_diagnostic_steps]:
            evidence = await plugin.collect_evidence(context, self.mcp_clients)
            trace.evidence.extend(evidence)
            systems = ", ".join(plugin.supported_systems)
            trace.diagnostic_steps.append(
                DiagnosticStep(
                    system_checked=systems,
                    action_taken=f"Selected {plugin.name} diagnostic plugin.",
                    evidence_found=evidence,
                    conclusion=(
                        "Phase 1 placeholder collected interface evidence only; live logs "
                        "and metadata are not available through MCP yet."
                    ),
                )
            )
            interpreted = plugin.interpret(evidence)
            if interpreted is not None:
                root_cause = interpreted
                trace.root_cause = interpreted
                break

        systems_checked = [
            system
            for plugin in matching_plugins[: self.settings.max_diagnostic_steps]
            for system in plugin.supported_systems
        ]
        trace.suggested_fixes.append(self._context_fix())
        self.trace_recorder.write(trace)

        if root_cause is not None:
            status = "diagnosed"
            answer = root_cause.summary
        else:
            status = "needs_more_context"
            answer = (
                f"{self._model_summary(request)} Trailwarden selected "
                f"{', '.join(systems_checked)} diagnostics, but live MCP clients are "
                "not wired yet. "
                "Provide configured MCP servers to collect logs and confirm a root cause."
            )

        return TrailwardenResponse(
            status=status,
            answer=answer,
            root_cause=root_cause,
            evidence=trace.evidence,
            suggested_fixes=trace.suggested_fixes,
            systems_checked=systems_checked,
            trace_id=request.trace_id,
        )

    @staticmethod
    def _default_plugins() -> tuple[DiagnosticPlugin, ...]:
        """Return the built-in placeholder diagnostic plugins."""
        return (
            AirflowDiagnosticPlugin(),
            DbtDiagnosticPlugin(),
            TrinoDiagnosticPlugin(),
            KubernetesDiagnosticPlugin(),
        )

    def _model_summary(self, request: TrailwardenRequest) -> str:
        """Ask the configured model for skeleton text, or return the placeholder text."""
        turn = self.backend.complete(
            system=self.system_prompt,
            messages=[Message(role="user", content=request.incident_text)],
            tools=[],
        )
        return turn.content

    @staticmethod
    def _context_fix() -> SuggestedFix:
        """Return the Phase 1 next step instead of pretending to fix production."""
        return SuggestedFix(
            title="Wire live diagnostic evidence sources",
            description=(
                "Configure the relevant MCP server and rerun the diagnosis so Trailwarden "
                "can read run history, logs, query metadata, and runtime events."
            ),
            risk="low",
            verification_step=(
                "Confirm the MCP server exposes read-only tools for the target system and "
                "that a new trace records evidence from that server."
            ),
        )

    @staticmethod
    def _load_system_prompt(path: Path) -> str:
        """Load the system prompt, falling back to a minimal role prompt."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "You are Trailwarden, a data engineering incident diagnostician."
