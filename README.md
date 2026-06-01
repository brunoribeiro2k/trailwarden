# Trailwarden

A data engineering support agent - the on-call diagnostician for data pipelines.

Trailwarden reads across orchestration and runtime systems to reconstruct what happened during
a failed pipeline run, identify the likely root cause, and suggest an actionable fix. It is
modeled structurally after Lorekeeper: the same compact Python skeleton, but aimed at incident
diagnosis instead of answering data questions or generating SQL.

## What It Does

Trailwarden starts from an incident description such as:

```text
Airflow DAG customer_orders failed last night
```

It is designed to:

1. Identify the orchestrator run or task involved.
2. Read orchestration history and logs.
3. Follow the execution trail into runtime systems called by the orchestrator.
4. Correlate timestamps, task ids, query ids, pod ids, cluster ids, job ids, and metadata.
5. Separate symptoms from root cause.
6. Return a concise diagnosis with evidence, confidence, impact, and a suggested fix.

Phase 1 is intentionally a runnable skeleton. Live integrations are represented by MCP
configuration and plugin interfaces, not hard-coded SDK clients.

## Architecture

```text
┌──────────────────────────────────────────────────────────┐
│  On-call / Chat / Future orchestrators                   │
└───────────────────────────┬──────────────────────────────┘
                            │ incident text + context
                            ▼
┌──────────────────────────────────────────────────────────┐
│  Trailwarden                                             │
│  src/trailwarden/agent/       -> runtime orchestration   │
│  src/trailwarden/diagnostics/ -> pluggable system logic  │
│  src/trailwarden/mcp/         -> MCP client boundary     │
│  src/trailwarden/model/       -> model backend protocol  │
│  src/trailwarden/core/        -> contracts + settings    │
│  src/trailwarden/observability/ -> JSONL traces          │
└────────────┬───────────┬───────────┬───────────┬─────────┘
             │           │           │           │
             ▼           ▼           ▼           ▼
       Airflow MCP   dbt MCP    Trino MCP   Kubernetes MCP
             │           │           │           │
             └───────────┴──── EMR / cloud runtime MCP ───┘
```

MCP servers are external processes. Trailwarden only knows about their configured URLs,
available tools, and normalized tool-call results. Direct communication with Airflow, dbt,
Trino, Kubernetes, EMR, or cloud logs belongs behind MCP servers.

## Pluggable Diagnostics

Each external system gets a diagnostic plugin with a narrow interface:

- `name`
- `supported_systems`
- `can_handle(context)`
- `collect_evidence(context, mcp_clients)`
- `interpret(evidence)`

The initial Airflow, dbt, Trino, and Kubernetes plugins are placeholders. They establish the
contract for future live evidence collection without making production calls.

## Setup

```bash
uv sync
cp .env.example .env
```

MCP servers are not installed or started by this project. Configure them separately as they
become available, then point the `TRAILWARDEN_*_MCP_URL` settings at those processes.

## Model Backends

Trailwarden expects a live LLM for normal interactive use. Environment variables select a named
profile, and each profile declares the backend class plus provider-specific model details in
`config/model-profiles.yaml`.

Local Ollama/Qwen development:

```bash
ollama pull qwen2.5:14b
TRAILWARDEN_LLM_PROFILE=local-qwen \
uv run trailwarden "Airflow DAG customer_orders failed last night"
```

Cloud providers use the same Trailwarden backend boundary; configure the provider credentials
expected by LiteLLM and change the selected profile, for example:

```bash
TRAILWARDEN_LLM_PROFILE=anthropic-claude \
uv run trailwarden "dbt model fct_orders failed in production"
```

Add new providers by adding profiles to `config/model-profiles.yaml`, such as an OpenAI model
profile, without adding provider-specific environment variables. The `disabled` profile is only
for tests, CI, and plumbing checks where no model server should be contacted.

## Usage

```bash
trailwarden
trailwarden "Airflow DAG customer_orders failed last night"
trailwarden --dag-id customer_orders --run-id manual__2026-05-30T23:00:00 "diagnose this failure"
trailwarden --verbose "dbt model fct_orders failed in production"
```

Running `trailwarden` without an incident opens an interactive shell. Enter incidents at the
`trailwarden>` prompt; use `/help`, `/verbose`, `/exit`, or `/quit` inside the shell.

Until live MCP clients are wired, the LLM can understand conversational incident text and select
intended diagnostics, but Trailwarden cannot confirm a production root cause. Real diagnosis
still depends on read-only evidence from configured MCP servers.

## Current Status

Phase 1:

- Python 3.13+ `uv` project
- Typer CLI entry point
- Pydantic contracts for requests, evidence, root causes, fixes, responses, and traces
- Swappable model backend protocol with not-configured and LiteLLM-backed adapters
- MCP client boundary and server config construction
- Pluggable diagnostic interfaces and placeholder plugins
- JSONL trace recorder
- Versioned system prompt in `prompts/`
- Eval harness skeleton
- Focused pytest tests

Phase 2:

- Wire concrete MCP transports.
- Add real Airflow run/task history collection.
- Add runtime correlation for dbt, Trino, Kubernetes, and EMR/cloud logs.
- Add model-backed reasoning over collected evidence.
- Expand eval incidents with known root causes.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run python evals/run_eval.py
```

## Guardrails

- Trailwarden must not mutate production systems by default.
- No retries, restarts, deletes, backfills, or config changes are allowed in this skeleton.
- Any future action mode must be explicit, guarded, audited, and separate from diagnosis.
- Evidence should be cited with source system, identifier, timestamp, severity, and raw reference.
- Unknowns should be stated directly instead of filled in with assumptions.
