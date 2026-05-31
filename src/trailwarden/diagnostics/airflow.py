"""Airflow diagnostic plugin placeholder."""

from __future__ import annotations

from trailwarden.diagnostics.base import KeywordDiagnosticPlugin


class AirflowDiagnosticPlugin(KeywordDiagnosticPlugin):
    """Select Airflow incidents and define the future Airflow evidence boundary."""

    name = "airflow"
    supported_systems = ("airflow",)
    keywords = ("airflow", "dag", "task instance", "task_id", "dag_id")
