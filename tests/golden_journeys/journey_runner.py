from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class ModelProfile:
    name: str
    base_url: str
    model: str
    backend_id: str = "llama_cpp"
    supports_vision: bool = False
    max_context_tokens: int = 16384
    max_output_tokens: int = 2048
    enable_thinking: bool = False

    @property
    def selector_value(self) -> str:
        return f"{self.backend_id}::{self.model}"

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ModelProfile":
        return cls(
            name=str(payload.get("name") or payload.get("model") or "local-model"),
            base_url=str(payload["base_url"]).rstrip("/"),
            model=str(payload["model"]),
            backend_id=str(payload.get("backend_id") or "llama_cpp"),
            supports_vision=bool(payload.get("supports_vision", False)),
            max_context_tokens=int(payload.get("max_context_tokens", 16384)),
            max_output_tokens=int(payload.get("max_output_tokens", 2048)),
            enable_thinking=bool(payload.get("enable_thinking", False)),
        )


def load_model_profiles() -> List[ModelProfile]:
    raw_profiles = os.environ.get("AIRPET_GOLDEN_MODEL_PROFILES", "").strip()
    if raw_profiles:
        payload = json.loads(raw_profiles)
        if not isinstance(payload, list):
            raise ValueError("AIRPET_GOLDEN_MODEL_PROFILES must be a JSON array.")
        return [ModelProfile.from_dict(item) for item in payload]

    base_url = os.environ.get("AIRPET_GOLDEN_MODEL_URL", "").strip()
    model = os.environ.get("AIRPET_GOLDEN_MODEL_NAME", "").strip()
    if not base_url or not model:
        return []
    return [
        ModelProfile(
            name=os.environ.get("AIRPET_GOLDEN_PROFILE_NAME", "local-model"),
            base_url=base_url,
            model=model,
            supports_vision=os.environ.get("AIRPET_GOLDEN_MODEL_VISION") == "1",
            max_context_tokens=int(
                os.environ.get("AIRPET_GOLDEN_CONTEXT_TOKENS", "16384")
            ),
            max_output_tokens=int(
                os.environ.get("AIRPET_GOLDEN_OUTPUT_TOKENS", "2048")
            ),
            enable_thinking=os.environ.get("AIRPET_GOLDEN_ENABLE_THINKING") == "1",
        )
    ]


@dataclass
class JourneyRecorder:
    journey: str
    profile: ModelProfile
    started_at: float = field(default_factory=time.monotonic)
    events: List[Dict[str, Any]] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    failure: str | None = None

    def capture_events(self, page) -> None:
        self.events = page.evaluate("window.__airpetGoldenEvents || []")

    def checkpoint(self, name: str, payload: Any) -> None:
        self.checkpoints.append({"name": name, "payload": payload})

    def write(self) -> Path:
        output_root = Path(
            os.environ.get(
                "AIRPET_GOLDEN_ARTIFACT_DIR",
                "/tmp/airpet-golden-journeys",
            )
        )
        output_root.mkdir(parents=True, exist_ok=True)
        safe_profile = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.profile.name)
        safe_journey = re.sub(r"[^A-Za-z0-9_.-]+", "-", self.journey)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = output_root / f"{timestamp}-{safe_profile}-{safe_journey}.json"

        model_responses = [
            event for event in self.events if event.get("type") == "model_response"
        ]
        tool_events = [
            event for event in self.events if event.get("type") == "tool_calls"
        ]
        tool_results = [
            event for event in self.events if event.get("type") == "tool_result"
        ]
        payload = {
            "schema_version": 1,
            "journey": self.journey,
            "profile": self.profile.__dict__,
            "elapsed_seconds": round(time.monotonic() - self.started_at, 3),
            "turn_count": len(model_responses),
            "tool_calls": [
                tool
                for event in tool_events
                for tool in (event.get("tools") or [])
            ],
            "failed_tool_results": [
                {
                    "turn": event.get("turn"),
                    "tool": event.get("tool"),
                    "error": event.get("error"),
                }
                for event in tool_results
                if event.get("success") is not True
            ],
            "model_turns": [
                {
                    "turn": event.get("turn"),
                    "elapsed_seconds": event.get("elapsed_seconds"),
                    "prompt_tokens": (event.get("usage") or {}).get(
                        "prompt_tokens"
                    ),
                    "completion_tokens": (event.get("usage") or {}).get(
                        "completion_tokens"
                    ),
                }
                for event in model_responses
            ],
            "failure": self.failure,
            "events": self.events,
            "checkpoints": self.checkpoints,
        }
        output_path.write_text(json.dumps(payload, indent=2, default=str))
        return output_path


def install_browser_telemetry(page) -> None:
    page.add_init_script(
        """
        window.__airpetGoldenEvents = JSON.parse(
            sessionStorage.getItem('airpetGoldenEvents') || '[]'
        );
        window.addEventListener('airpet:ai-progress', (event) => {
            window.__airpetGoldenEvents.push({
                ...event.detail,
                browser_timestamp_ms: Date.now(),
            });
            sessionStorage.setItem(
                'airpetGoldenEvents',
                JSON.stringify(window.__airpetGoldenEvents)
            );
        });
        """
    )


def configure_runtime_profile(page, profile: ModelProfile) -> None:
    runtime_config = {
        "backends": {
            profile.backend_id: {
                "enabled": True,
                "base_url": profile.base_url,
                "endpoint_path": "/v1/chat/completions",
                "model": profile.model,
                "timeout_seconds": 300,
                "max_retries": 0,
                "retry_backoff_seconds": 0,
                "verify_tls": True,
                "supports_vision": profile.supports_vision,
                "max_context_tokens": profile.max_context_tokens,
                "max_output_tokens": profile.max_output_tokens,
                "enable_thinking": profile.enable_thinking,
                "headers": {},
            },
        },
    }
    result = page.evaluate(
        """async (runtimeConfig) => {
            const response = await fetch('/api/ai/backends/runtime_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({runtime_config: runtimeConfig}),
            });
            return {ok: response.ok, body: await response.json()};
        }""",
        runtime_config,
    )
    assert result["ok"], result


def send_ai_prompt(page, prompt: str, *, timeout_ms: int = 180000) -> None:
    page.locator("#ai_prompt_input").fill(prompt)
    page.locator("#ai_generate_button").click()
    page.locator("#ai_generate_button.loading").wait_for(
        state="attached",
        timeout=10000,
    )
    page.locator("#ai_generate_button.loading").wait_for(
        state="detached",
        timeout=timeout_ms,
    )


def fetch_project_state(page) -> Dict[str, Any]:
    result = page.evaluate(
        """async () => {
            const response = await fetch('/get_project_state');
            return {ok: response.ok, body: await response.json()};
        }"""
    )
    assert result["ok"], result
    return result["body"]
