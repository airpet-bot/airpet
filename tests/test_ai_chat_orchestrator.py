from src.ai_backend_adapters import TextGenerationResponse, TextMessage
from src.ai_chat_orchestrator import (
    ProviderIndependentChatOrchestrator,
    resolve_chat_generation_policy,
)


def test_generation_policy_defaults_to_bounded_tool_focused_local_turns():
    policy = resolve_chat_generation_policy("llama_cpp", {})

    assert policy.max_output_tokens == 2048
    assert policy.temperature is None
    assert policy.extended_reasoning is False


def test_generation_policy_uses_runtime_overrides_and_bounds_invalid_values():
    policy = resolve_chat_generation_policy(
        "llama_cpp",
        {
            "backends": {
                "llama_cpp": {
                    "max_output_tokens": 4096,
                    "temperature": "0.15",
                    "enable_thinking": "true",
                },
            },
        },
    )

    assert policy.max_output_tokens == 4096
    assert policy.temperature == 0.15
    assert policy.extended_reasoning is True

    bounded = resolve_chat_generation_policy(
        "llama_cpp",
        {"backends": {"llama_cpp": {"max_output_tokens": 1}}},
    )
    assert bounded.max_output_tokens == 64


def test_orchestrator_builds_normalized_request_and_records_turn_timing():
    calls = []

    def fake_invoke(backend_id, request, runtime_config=None):
        calls.append((backend_id, request, runtime_config))
        return TextGenerationResponse(
            backend_id=backend_id,
            text="Done.",
            raw_response={"choices": []},
            model="local-model",
            usage={"completion_tokens": 3},
        )

    runtime_config = {
        "backends": {
            "llama_cpp": {
                "max_output_tokens": 1024,
                "enable_thinking": False,
            },
        },
    }
    orchestrator = ProviderIndependentChatOrchestrator(
        "llama_cpp",
        runtime_config,
        fake_invoke,
    )
    request = orchestrator.build_request(
        messages=[TextMessage(role="user", content="Create a box.")],
        require_tools=True,
        require_json_mode=True,
        require_vision=False,
        require_streaming=False,
        min_context_tokens=8000,
        tool_schemas=(
            {
                "type": "function",
                "function": {
                    "name": "create_box",
                    "parameters": {"type": "object"},
                },
            },
        ),
        tool_choice="auto",
    )

    result = orchestrator.invoke_turn(request)

    assert request.max_output_tokens == 1024
    assert request.require_tools is True
    assert calls[0][0] == "llama_cpp"
    assert calls[0][2] == runtime_config
    assert result.response.text == "Done."
    assert result.elapsed_seconds >= 0
    assert orchestrator.request_event(turn=2)["generation_policy"] == {
        "max_output_tokens": 1024,
        "temperature": None,
        "extended_reasoning": False,
    }
    assert result.response_event(turn=2)["usage"] == {"completion_tokens": 3}
