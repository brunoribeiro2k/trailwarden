"""Model backend interfaces used by the diagnostic runtime."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import yaml
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from trailwarden.core.config import Settings


class Message(BaseModel):
    """A single conversation turn sent to a model backend."""

    role: str
    content: str | list[dict[str, Any]]


class ToolDefinition(BaseModel):
    """Tool metadata exposed to a model."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ModelTurn(BaseModel):
    """A model response for one diagnostic-loop turn."""

    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    stop_reason: str = "stop"


class ModelProfile(BaseModel):
    """Model-provider settings loaded from the model profile registry."""

    backend_class: str = "LiteLLMBackend"
    model: str = "none"
    api_base: str | None = None
    temperature: float = 0.2
    timeout_seconds: float = 60.0


class ModelProfileRegistry(BaseModel):
    """Named model profiles kept outside environment variables."""

    profiles: dict[str, ModelProfile] = Field(default_factory=dict)


class ModelBackend(Protocol):
    """Common interface for future Anthropic, Ollama, and test backends."""

    name: str
    model: str

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
    ) -> ModelTurn:
        """Run one model turn."""
        ...


class NotConfiguredBackend:
    """Placeholder backend used until a concrete model adapter is wired."""

    name = "not-configured"
    model = "none"

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
    ) -> ModelTurn:
        """Return a clear skeleton response instead of calling a live model."""
        del system, messages, tools
        return ModelTurn(
            content=(
                "Trailwarden's Phase 1 skeleton is ready. Live model adapters and MCP "
                "transports are not wired yet, so this run can identify intended systems "
                "but cannot confirm a production root cause."
            )
        )


class LiteLLMBackend:
    """Model backend backed by LiteLLM's provider-neutral completion API."""

    name = "litellm"

    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        temperature: float = 0.2,
        timeout_seconds: float = 60.0,
        completion_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.model = model
        self.api_base = api_base
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self._completion_fn = completion_fn

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[ToolDefinition],
    ) -> ModelTurn:
        """Run a non-streaming model turn through LiteLLM."""
        completion = self._completion_fn or self._load_completion_fn()
        payload = {
            "model": self.model,
            "messages": self._build_messages(system, messages),
            "temperature": self.temperature,
            "timeout": self.timeout_seconds,
        }
        if self.api_base:
            payload["api_base"] = self.api_base
        if tools:
            payload["tools"] = [self._tool_to_payload(tool) for tool in tools]

        response = completion(**payload)
        return self._turn_from_response(response)

    @staticmethod
    def _load_completion_fn() -> Callable[..., Any]:
        """Import LiteLLM lazily so tests can inject a fake completion function."""
        from litellm import completion

        return completion

    @staticmethod
    def _build_messages(system: str, messages: list[Message]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(message.model_dump() for message in messages)
        return payload

    @staticmethod
    def _tool_to_payload(tool: ToolDefinition) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    @classmethod
    def _turn_from_response(cls, response: Any) -> ModelTurn:
        choice = cls._get(cls._get(response, "choices", [None]), 0)
        message = cls._get(choice, "message", {}) or {}
        content = cls._get(message, "content", "") or ""
        tool_calls = cls._normalize_tool_calls(cls._get(message, "tool_calls", []) or [])
        stop_reason = cls._get(choice, "finish_reason", "stop") or "stop"
        return ModelTurn(content=content, tool_calls=tool_calls, stop_reason=stop_reason)

    @classmethod
    def _normalize_tool_calls(cls, tool_calls: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for call in tool_calls:
            if isinstance(call, BaseModel):
                normalized.append(call.model_dump(mode="json"))
            elif isinstance(call, dict):
                normalized.append(call)
            else:
                normalized.append(cls._object_to_dict(call))
        return normalized

    @classmethod
    def _object_to_dict(cls, value: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in ("id", "type", "function"):
            item = cls._get(value, key, None)
            if item is not None:
                result[key] = item
        function = result.get("function")
        if function is not None and not isinstance(function, dict):
            result["function"] = cls._object_to_dict(function)
        return result

    @staticmethod
    def _get(value: Any, key: Any, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(key, default)
        if isinstance(key, int):
            try:
                return value[key]
            except (IndexError, KeyError, TypeError):
                return default
        return getattr(value, key, default)


def build_model_backend(settings: Settings) -> ModelBackend:
    """Build the configured model backend."""
    profile = load_model_profile(settings.llm_config_path, settings.llm_profile)
    backend_class = profile.backend_class.strip()
    if backend_class == "NotConfiguredBackend":
        return NotConfiguredBackend()
    if backend_class == "LiteLLMBackend":
        return LiteLLMBackend(
            model=profile.model,
            api_base=profile.api_base,
            temperature=profile.temperature,
            timeout_seconds=profile.timeout_seconds,
        )
    raise ValueError(
        f"Unsupported backend_class {profile.backend_class!r} in model profile "
        f"{settings.llm_profile!r}. Expected 'NotConfiguredBackend' or 'LiteLLMBackend'."
    )


def load_model_profile(path: Path, profile_name: str) -> ModelProfile:
    """Load one named model profile from a YAML registry."""
    if not path.exists():
        raise ValueError(f"Model profile config not found: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    registry = ModelProfileRegistry.model_validate(payload)
    try:
        return registry.profiles[profile_name]
    except KeyError as error:
        available = ", ".join(sorted(registry.profiles)) or "none"
        raise ValueError(
            f"Unknown TRAILWARDEN_LLM_PROFILE {profile_name!r}. "
            f"Available profiles: {available}."
        ) from error
