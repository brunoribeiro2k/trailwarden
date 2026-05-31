"""Trino diagnostic plugin placeholder."""

from __future__ import annotations

from trailwarden.diagnostics.base import KeywordDiagnosticPlugin


class TrinoDiagnosticPlugin(KeywordDiagnosticPlugin):
    """Select Trino incidents and define the future query evidence boundary."""

    name = "trino"
    supported_systems = ("trino",)
    keywords = ("trino", "query", "sql", "presto", "query_id")
