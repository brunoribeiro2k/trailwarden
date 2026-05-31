# Trailwarden

Trailwarden is a data engineering support agent: the on-call diagnostician for failed data
pipelines. It follows Lorekeeper's compact architecture, but diagnoses incidents across
orchestration and runtime systems instead of answering data questions.

## Current Phase

Phase 1 skeleton. The package, contracts, CLI, diagnostic plugin boundary, MCP boundary,
trace recorder, prompt, eval harness, and tests are in place. Live MCP transports and model
adapters are future work.

## Tech Stack

- Python 3.13+
- `uv` for dependency and environment management
- Typer CLI
- Pydantic and pydantic-settings
- MCP servers as external processes
- JSONL traces under `.trailwarden/traces`

## Key Commands

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run trailwarden --verbose "Airflow DAG customer_orders failed last night"
```

## Guardrails

Trailwarden is diagnostic-only by default. Do not add retries, restarts, deletes, backfills,
or configuration changes unless a future explicit guarded action mode is designed first.
