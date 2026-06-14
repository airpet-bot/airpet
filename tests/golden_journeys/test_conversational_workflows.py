from __future__ import annotations

import json
import os
import socket
import sys
from urllib.parse import urlparse

import pytest

_LOCAL_PACKAGES = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    ".local-packages",
)
if _LOCAL_PACKAGES not in sys.path:
    sys.path.insert(0, _LOCAL_PACKAGES)

from playwright.sync_api import sync_playwright

from tests.golden_journeys.journey_runner import (
    JourneyRecorder,
    configure_runtime_profile,
    fetch_project_state,
    install_browser_telemetry,
    load_model_profiles,
    send_ai_prompt,
)


AIRPET_URL = os.environ.get("AIRPET_GOLDEN_URL", "http://127.0.0.1:5005")
MODEL_PROFILES = load_model_profiles()


def _server_is_running(url: str) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection(
            (parsed.hostname or "127.0.0.1", parsed.port or 80),
            timeout=2,
        ):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.skipif(
        not MODEL_PROFILES,
        reason="Set AIRPET_GOLDEN_MODEL_URL and AIRPET_GOLDEN_MODEL_NAME.",
    ),
    pytest.mark.skipif(
        not _server_is_running(AIRPET_URL),
        reason=f"AIRPET server not running at {AIRPET_URL}.",
    ),
]


@pytest.fixture(params=MODEL_PROFILES or [None], ids=lambda item: item.name if item else "unconfigured")
def model_profile(request):
    return request.param


@pytest.fixture
def golden_page(model_profile):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        install_browser_telemetry(page)
        page.goto(AIRPET_URL, wait_until="networkidle")
        configure_runtime_profile(page, model_profile)
        page.reload(wait_until="networkidle")
        page.evaluate(
            """() => {
                window.__airpetGoldenEvents = [];
                sessionStorage.removeItem('airpetGoldenEvents');
            }"""
        )
        page.locator("#ai_advanced_settings").evaluate(
            "(element) => { element.open = true; }"
        )
        page.locator("#ai_execution_mode").select_option("interactive")
        page.locator("#ai_model_select").select_option(model_profile.selector_value)
        page.on("dialog", lambda dialog: dialog.accept())
        yield page
        browser.close()


def _run_recorded(journey, model_profile, page, callback):
    recorder = JourneyRecorder(journey=journey, profile=model_profile)
    try:
        callback(recorder)
    except Exception as exc:
        recorder.failure = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        recorder.capture_events(page)
        recorder.write()


def test_geometry_adjustment_undo_and_reload(model_profile, golden_page):
    page = golden_page

    def journey(recorder):
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()

        send_ai_prompt(
            page,
            (
                "Design-only task. Use AIRPET geometry tools now. Create one "
                "silicon detector tile named golden_tile with full dimensions "
                "6 mm x 6 mm x 2 mm, place it at the world origin, and make its "
                "logical volume sensitive. Do not run a simulation."
            ),
        )
        created_state = fetch_project_state(page)
        recorder.checkpoint("created", created_state)
        assert "golden_tile" in json.dumps(created_state).lower()

        send_ai_prompt(
            page,
            (
                "Move the physical placement for golden_tile by exactly +15 mm "
                "along x. Keep y, z, rotation, material, dimensions, and "
                "sensitive-detector state unchanged. Use the focused geometry "
                "inspection tool before or after the edit."
            ),
        )
        moved_state = fetch_project_state(page)
        recorder.checkpoint("moved", moved_state)
        assert moved_state != created_state

        page.get_by_role("button", name="Edit", exact=True).click()
        page.locator("#undoButton").click()
        page.wait_for_timeout(1000)
        undone_state = fetch_project_state(page)
        recorder.checkpoint("undone", undone_state)
        assert undone_state != moved_state

        page.reload(wait_until="networkidle")
        reloaded_state = fetch_project_state(page)
        recorder.checkpoint("reloaded", reloaded_state)
        assert reloaded_state == undone_state

        events = page.evaluate("window.__airpetGoldenEvents || []")
        assert any(event.get("type") == "tool_calls" for event in events)
        assert not any(event.get("type") == "error" for event in events)

    _run_recorded(
        "geometry-adjustment-undo-reload",
        model_profile,
        page,
        journey,
    )


@pytest.mark.skipif(
    os.environ.get("AIRPET_GOLDEN_FULL_SIMULATION") != "1",
    reason="Set AIRPET_GOLDEN_FULL_SIMULATION=1 for the Geant4 journey.",
)
def test_source_readout_simulation_monitoring_and_analysis(model_profile, golden_page):
    page = golden_page

    def journey(recorder):
        page.locator("#ai_execution_mode").select_option("build_validate")
        send_ai_prompt(
            page,
            (
                "Create a minimal silicon slab detector, make it sensitive, "
                "configure a 1 MeV gamma pencil beam aimed through it, save "
                "events that hit that detector, run 20 events, monitor the run, "
                "and summarize the resulting scoring analysis."
            ),
            timeout_ms=300000,
        )
        state = fetch_project_state(page)
        recorder.checkpoint("completed_study", state)
        events = page.evaluate("window.__airpetGoldenEvents || []")
        tool_names = [
            name
            for event in events
            if event.get("type") == "tool_calls"
            for name in event.get("tools", [])
        ]
        assert "run_simulation" in tool_names or "run_detector_study" in tool_names
        assert not any(event.get("type") == "error" for event in events)

    _run_recorded(
        "source-readout-simulation-analysis",
        model_profile,
        page,
        journey,
    )


def test_visual_repair_checkpoint(model_profile, golden_page):
    if not model_profile.supports_vision:
        pytest.skip("Model profile is not marked vision-capable.")
    page = golden_page

    def journey(recorder):
        send_ai_prompt(
            page,
            (
                "Create a compact 2 by 2 array of four silicon tiles named "
                "visual_tile_00 through visual_tile_11 with 10 mm pitch."
            ),
        )
        page.locator("#ai_visual_check_button").click()
        page.locator("#ai_generate_button.loading").wait_for(
            state="attached",
            timeout=10000,
        )
        page.locator("#ai_generate_button.loading").wait_for(
            state="detached",
            timeout=240000,
        )
        events = page.evaluate("window.__airpetGoldenEvents || []")
        recorder.checkpoint("post_visual_check", fetch_project_state(page))
        assert any(event.get("type") == "model_response" for event in events)
        assert not any(event.get("type") == "error" for event in events)

    _run_recorded("visual-repair-checkpoint", model_profile, page, journey)
