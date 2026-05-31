"""Tests for swappable model backends."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from trailwarden.core.config import Settings
from trailwarden.model.backend import (
    LiteLLMBackend,
    Message,
    NotConfiguredBackend,
    ToolDefinition,
    build_model_backend,
    load_model_profile,
)


def test_build_model_backend_defaults_to_local_profile() -> None:
    """Default settings select the local Ollama/Qwen profile for development."""
    backend = build_model_backend(Settings())

    assert isinstance(backend, LiteLLMBackend)
    assert backend.model == "ollama/qwen2.5:14b"
    assert backend.api_base == "http://localhost:11434"


def test_build_model_backend_can_select_disabled_profile(tmp_path: Path) -> None:
    """The profile registry can still select the placeholder backend explicitly."""
    config_path = tmp_path / "model-profiles.yaml"
    config_path.write_text(
        """
profiles:
  disabled:
    backend_class: NotConfiguredBackend
""",
        encoding="utf-8",
    )

    backend = build_model_backend(Settings(llm_profile="disabled", llm_config_path=config_path))

    assert isinstance(backend, NotConfiguredBackend)


def test_build_model_backend_creates_litellm_backend(tmp_path: Path) -> None:
    """The litellm backend is configured from the selected model profile."""
    config_path = tmp_path / "model-profiles.yaml"
    config_path.write_text(
        """
profiles:
  dev:
    backend_class: LiteLLMBackend
    model: ollama/qwen2.5:14b
    api_base: http://localhost:11434
    temperature: 0.1
    timeout_seconds: 30
""",
        encoding="utf-8",
    )
    settings = Settings(
        llm_profile="dev",
        llm_config_path=config_path,
    )

    backend = build_model_backend(settings)

    assert isinstance(backend, LiteLLMBackend)
    assert backend.model == "ollama/qwen2.5:14b"
    assert backend.api_base == "http://localhost:11434"
    assert backend.temperature == 0.1
    assert backend.timeout_seconds == 30


def test_load_model_profile_rejects_missing_profile(tmp_path: Path) -> None:
    """Unknown profile names report available choices."""
    config_path = tmp_path / "model-profiles.yaml"
    config_path.write_text(
        """
profiles:
  local-qwen:
    model: ollama/qwen2.5:14b
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Available profiles: local-qwen"):
        load_model_profile(config_path, "prod")


def test_build_model_backend_rejects_mismatched_profile_backend(tmp_path: Path) -> None:
    """Unsupported backend class names fail with an actionable error."""
    config_path = tmp_path / "model-profiles.yaml"
    config_path.write_text(
        """
profiles:
  dev:
    backend_class: MysteryBackend
    model: mystery/model
""",
        encoding="utf-8",
    )
    settings = Settings(
        llm_profile="dev",
        llm_config_path=config_path,
    )

    with pytest.raises(ValueError, match="Unsupported backend_class"):
        build_model_backend(settings)


def test_litellm_backend_maps_request_and_response() -> None:
    """LiteLLMBackend converts Trailwarden messages and returns a ModelTurn."""
    captured: dict[str, object] = {}

    def fake_completion(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "content": "diagnostic summary",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "airflow_get_task_log",
                                    "arguments": '{"task_id": "load_orders"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }

    backend = LiteLLMBackend(
        model="ollama/qwen2.5:14b",
        api_base="http://localhost:11434",
        temperature=0.2,
        timeout_seconds=60,
        completion_fn=fake_completion,
    )

    turn = backend.complete(
        system="You are Trailwarden.",
        messages=[Message(role="user", content="Airflow DAG failed")],
        tools=[
            ToolDefinition(
                name="airflow_get_task_log",
                description="Read a task log.",
                input_schema={
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                },
            )
        ],
    )

    assert captured["model"] == "ollama/qwen2.5:14b"
    assert captured["api_base"] == "http://localhost:11434"
    assert captured["temperature"] == 0.2
    assert captured["timeout"] == 60
    assert captured["messages"] == [
        {"role": "system", "content": "You are Trailwarden."},
        {"role": "user", "content": "Airflow DAG failed"},
    ]
    assert captured["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "airflow_get_task_log",
                "description": "Read a task log.",
                "parameters": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                },
            },
        }
    ]
    assert turn.content == "diagnostic summary"
    assert turn.stop_reason == "tool_calls"
    assert turn.tool_calls == [
        {
            "id": "call-1",
            "type": "function",
            "function": {
                "name": "airflow_get_task_log",
                "arguments": '{"task_id": "load_orders"}',
            },
        }
    ]


def test_litellm_backend_accepts_object_responses() -> None:
    """LiteLLM response objects are normalized as well as plain dictionaries."""
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="ok", tool_calls=[]),
                finish_reason="stop",
            )
        ]
    )
    backend = LiteLLMBackend(
        model="anthropic/claude-sonnet-4-6",
        completion_fn=lambda **_: response,
    )

    turn = backend.complete(system="", messages=[], tools=[])

    assert turn.content == "ok"
    assert turn.tool_calls == []
    assert turn.stop_reason == "stop"
