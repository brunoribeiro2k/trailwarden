"""Trace recording for Trailwarden runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from trailwarden.core.contracts import TrailwardenTrace


class TraceRecorder:
    """Persist Trailwarden traces as JSONL for debugging and eval analysis."""

    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir

    def write(self, trace: TrailwardenTrace) -> Path:
        """Append a trace to the daily JSONL trace file."""
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        trace.finished_at = trace.finished_at or datetime.now(UTC)
        path = self.trace_dir / f"{trace.started_at.date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(trace.model_dump(mode="json"), sort_keys=True))
            handle.write("\n")
        return path
