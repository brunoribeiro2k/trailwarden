"""dbt diagnostic plugin placeholder."""

from __future__ import annotations

from trailwarden.diagnostics.base import KeywordDiagnosticPlugin


class DbtDiagnosticPlugin(KeywordDiagnosticPlugin):
    """Select dbt incidents and define the future dbt evidence boundary."""

    name = "dbt"
    supported_systems = ("dbt",)
    keywords = ("dbt", "model", "source freshness", "test failure", "manifest")
