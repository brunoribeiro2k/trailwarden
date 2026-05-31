"""Kubernetes diagnostic plugin placeholder."""

from __future__ import annotations

from trailwarden.diagnostics.base import KeywordDiagnosticPlugin


class KubernetesDiagnosticPlugin(KeywordDiagnosticPlugin):
    """Select Kubernetes incidents and define the future pod log evidence boundary."""

    name = "kubernetes"
    supported_systems = ("kubernetes",)
    keywords = ("kubernetes", "k8s", "pod", "container", "oomkilled", "namespace")
