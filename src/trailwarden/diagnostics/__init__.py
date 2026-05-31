"""Diagnostic plugins for orchestration and runtime systems."""

from trailwarden.diagnostics.airflow import AirflowDiagnosticPlugin
from trailwarden.diagnostics.dbt import DbtDiagnosticPlugin
from trailwarden.diagnostics.kubernetes import KubernetesDiagnosticPlugin
from trailwarden.diagnostics.trino import TrinoDiagnosticPlugin

__all__ = [
    "AirflowDiagnosticPlugin",
    "DbtDiagnosticPlugin",
    "KubernetesDiagnosticPlugin",
    "TrinoDiagnosticPlugin",
]
