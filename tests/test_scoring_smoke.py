"""
Playwright smoke test for the AIRPET scoring workflow.

Assumes the AIRPET dev server is running on http://localhost:5003.
Requires playwright (installed locally under .local-packages).
"""
import sys
import os
import socket

# Allow local playwright package to be found without global install
_LOCAL_PACKAGES = os.path.join(os.path.dirname(__file__), "..", ".local-packages")
if _LOCAL_PACKAGES not in sys.path:
    sys.path.insert(0, _LOCAL_PACKAGES)

import pytest
from playwright.sync_api import sync_playwright


def _server_is_running(host: str = "localhost", port: int = 5003) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not _server_is_running(), reason="AIRPET server not running on localhost:5003")
def test_scoring_smoke_sensitive_detector_simulation_and_analysis():
    """
    Run a full scoring smoke test:
    - Create a new geometry
    - Add a GPS source
    - Mark box_LV as a sensitive detector
    - Add a scoring mesh
    - Run a short simulation
    - Verify the Analysis button is enabled
    - Verify no uncaught JavaScript errors
    """
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture uncaught page errors
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # Capture console messages (we treat error-level logs as failures too)
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)

        # Navigate to the app and wait for initial load
        page.goto("http://localhost:5003", wait_until="networkidle")

        # --- Create a new geometry for a clean state ---
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()

        # Handle the confirm dialog
        page.on("dialog", lambda dialog: dialog.accept())

        # Wait for the scene to refresh after creating new geometry
        page.wait_for_timeout(2000)

        # --- Add a GPS source ---
        page.get_by_role("button", name="+ GPS").click()
        page.locator("input#gpsEditorName").fill("smoke_source")
        page.get_by_role("button", name="Create Source").click()
        page.wait_for_timeout(1000)

        # --- Mark box_LV as a sensitive detector ---
        page.get_by_role("button", name="Volumes").click()

        # Find and click the edit button (pencil icon) next to "box_LV"
        page.get_by_role("listitem").filter(has_text="box_LV").get_by_role("button", name="✏️").click()

        # Check the "Sensitive Detector" checkbox
        page.locator("input#lvEditorSensitive").check()

        # Click the "Update LV" button
        page.locator("button#confirmLVEditor").click()
        page.wait_for_timeout(1000)

        # --- Add a scoring mesh ---
        page.get_by_role("button", name="Properties").click()

        # Expand the "Scoring & Run Controls" accordion if not already expanded
        page.get_by_text("Scoring & Run Controls").first.click()

        # Click the "Add Scoring Mesh" button
        page.get_by_role("button", name="Add Scoring Mesh").click()
        page.wait_for_timeout(1000)

        # --- Ensure the source is active ---
        active_source_checkbox = page.locator("input.active-source-checkbox")
        if active_source_checkbox.count() > 0:
            assert active_source_checkbox.first.is_checked(), (
                "Expected the source active checkbox to be checked by default"
            )

        # --- Run the simulation ---
        page.get_by_role("button", name="Simulation").click()

        # Set the events input to 10
        page.locator("input#simEventsInput").fill("10")

        # Click the "Run" button
        page.locator("button#runSimButton").click()

        # Wait for the simulation to complete
        page.get_by_text("Simulation Completed").wait_for(timeout=120000)

        # --- Verify the Analysis button is enabled ---
        analysis_button = page.locator("button#analysisModalButton")
        assert analysis_button.is_enabled(), (
            "Expected the Analysis button to be enabled after simulation completed"
        )

        # --- Verify no uncaught JavaScript errors ---
        filtered_page_errors = [
            e for e in page_errors
            if "Password field is not contained in a form" not in e
        ]

        assert len(filtered_page_errors) == 0, (
            f"Uncaught JavaScript errors detected: {filtered_page_errors}"
        )
        assert len(console_errors) == 0, (
            f"Console error-level messages detected: {[str(m) for m in console_errors]}"
        )

        browser.close()
