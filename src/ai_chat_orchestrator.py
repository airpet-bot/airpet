from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from src.ai_backend_adapters import (
    TextGenerationRequest,
    TextGenerationResponse,
    TextMessage,
)


DEFAULT_LOCAL_MAX_OUTPUT_TOKENS = 2048


def _backend_runtime_config(
    runtime_config: Optional[Mapping[str, Any]],
    backend_id: str,
) -> Mapping[str, Any]:
    if not isinstance(runtime_config, Mapping):
        return {}
    backends = runtime_config.get("backends")
    if isinstance(backends, Mapping):
        backend_config = backends.get(backend_id)
        return backend_config if isinstance(backend_config, Mapping) else {}
    backend_config = runtime_config.get(backend_id)
    return backend_config if isinstance(backend_config, Mapping) else {}


def _bounded_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 64), 32768)


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


@dataclass(frozen=True)
class ChatGenerationPolicy:
    max_output_tokens: int = DEFAULT_LOCAL_MAX_OUTPUT_TOKENS
    temperature: Optional[float] = None
    extended_reasoning: bool = False

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "extended_reasoning": self.extended_reasoning,
        }


def resolve_chat_generation_policy(
    backend_id: str,
    runtime_config: Optional[Mapping[str, Any]] = None,
) -> ChatGenerationPolicy:
    backend_config = _backend_runtime_config(runtime_config, backend_id)
    return ChatGenerationPolicy(
        max_output_tokens=_bounded_positive_int(
            backend_config.get("max_output_tokens"),
            DEFAULT_LOCAL_MAX_OUTPUT_TOKENS,
        ),
        temperature=_optional_float(backend_config.get("temperature")),
        extended_reasoning=(
            _coerce_bool(backend_config.get("enable_thinking"), False)
            if backend_id == "llama_cpp"
            else False
        ),
    )


@dataclass(frozen=True)
class ChatTurnResult:
    response: TextGenerationResponse
    elapsed_seconds: float
    policy: ChatGenerationPolicy

    def response_event(self, *, turn: int) -> Dict[str, Any]:
        return {
            "type": "model_response",
            "turn": turn,
            "backend_id": self.response.backend_id,
            "model": self.response.model,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "usage": self.response.usage,
            "generation_policy": self.policy.as_public_dict(),
        }


class ProviderIndependentChatOrchestrator:
    """Build and execute one normalized local-backend chat turn."""

    def __init__(
        self,
        backend_id: str,
        runtime_config: Optional[Mapping[str, Any]],
        invoke: Callable[..., TextGenerationResponse],
    ):
        self.backend_id = backend_id
        self.runtime_config = runtime_config
        self.invoke = invoke
        self.policy = resolve_chat_generation_policy(backend_id, runtime_config)

    def request_event(self, *, turn: int) -> Dict[str, Any]:
        return {
            "type": "model_request_start",
            "turn": turn,
            "backend_id": self.backend_id,
            "generation_policy": self.policy.as_public_dict(),
        }

    def build_request(
        self,
        *,
        messages: Sequence[TextMessage],
        require_tools: bool,
        require_json_mode: bool,
        require_vision: bool,
        require_streaming: bool,
        min_context_tokens: Optional[int],
        tool_schemas: Optional[Tuple[Dict[str, Any], ...]],
        tool_choice: Optional[Any],
    ) -> TextGenerationRequest:
        return TextGenerationRequest(
            messages=tuple(messages),
            require_tools=require_tools,
            require_json_mode=require_json_mode,
            require_vision=require_vision,
            require_streaming=require_streaming,
            min_context_tokens=min_context_tokens,
            temperature=self.policy.temperature,
            max_output_tokens=self.policy.max_output_tokens,
            tool_schemas=tool_schemas,
            tool_choice=tool_choice,
        )

    def invoke_turn(self, request: TextGenerationRequest) -> ChatTurnResult:
        started_at = time.monotonic()
        response = self.invoke(
            self.backend_id,
            request,
            runtime_config=self.runtime_config,
        )
        return ChatTurnResult(
            response=response,
            elapsed_seconds=time.monotonic() - started_at,
            policy=self.policy,
        )
