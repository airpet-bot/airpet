"""
Playwright baseline test for AIRPET startup geometry, hierarchy, and console cleanliness.

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
def test_startup_geometry_hierarchy_and_console_cleanliness():
    """
    Verify that AIRPET loads with:
    - A visible 3D canvas
    - The default hierarchy (World -> box_PV)
    - No uncaught JavaScript errors
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

        # Ensure a clean default state by creating a new geometry
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()

        # Handle the confirm dialog
        page.on("dialog", lambda dialog: dialog.accept())

        # Wait for the scene to refresh after creating new geometry
        page.wait_for_timeout(2000)

        # --- Verify hierarchy ---
        # The default clean state should show "World" and "box_PV (LV: box_LV)"
        assert page.get_by_text("World").first.is_visible(), "Expected 'World' in hierarchy"
        assert page.get_by_text("box_PV (LV: box_LV)").first.is_visible(), (
            "Expected default box 'box_PV (LV: box_LV)' in hierarchy"
        )

        # --- Verify 3D canvas exists ---
        canvas = page.locator("canvas")
        assert canvas.count() > 0, "Expected at least one <canvas> element"
        assert canvas.first.is_visible(), "Expected 3D canvas to be visible"

        # --- Verify console cleanliness ---
        # Filter out known non-error verbose warnings that are not failures
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
