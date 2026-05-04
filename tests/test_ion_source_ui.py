"""
Playwright test for creating an ion source via the UI.

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
def test_ion_source_creation_and_persistence():
    """
    Verify that the UI can create an ion source, persist its parameters,
    and display them in the inspector without uncaught JS errors.
    """
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)

        page.goto("http://localhost:5003", wait_until="networkidle")

        # --- Create a new geometry for a clean state ---
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()
        page.on("dialog", lambda dialog: dialog.accept())
        page.wait_for_timeout(2000)

        # --- Open the particle source editor ---
        page.get_by_role("button", name="+ GPS").click()
        page.locator("input#gpsEditorName").fill("ion_test_source")

        # --- Switch to Ion source type ---
        page.locator("select#gpsEditorSourceType").select_option("ion")
        # Wait a moment for the UI toggle
        page.wait_for_timeout(300)

        # --- Fill ion parameters ---
        page.locator("input#gpsIonZ").fill("26")
        page.locator("input#gpsIonA").fill("56")
        page.locator("input#gpsIonQ").fill("2")
        page.locator("input#gpsIonE").fill("10.5")

        # --- Create the source ---
        page.get_by_role("button", name="Create Source").click()
        page.wait_for_timeout(1000)

        # --- Verify the source appears in the hierarchy ---
        assert page.get_by_text("ion_test_source").first.is_visible(), (
            "Expected 'ion_test_source' to appear in the hierarchy"
        )

        # --- Select the source in the hierarchy to open the inspector ---
        page.get_by_text("ion_test_source").first.click()
        page.wait_for_timeout(500)

        # --- Verify inspector shows ion parameters ---
        assert page.locator('label:has-text("Source Type:") + span').inner_text() == "ION"
        assert page.locator('label:has-text("Ion Z:") + span').inner_text() == "26"
        assert page.locator('label:has-text("Ion A:") + span').inner_text() == "56"
        assert page.locator('label:has-text("Ion Q:") + span').inner_text() == "2"
        assert page.locator('label:has-text("Excitation Energy (keV):") + span').inner_text() == "10.5"

        # --- Re-open the editor to verify round-trip persistence ---
        # Double-click the source text in the hierarchy to open the editor.
        page.get_by_text("ion_test_source").first.dblclick()
        page.wait_for_timeout(500)

        assert page.locator("select#gpsEditorSourceType").input_value() == "ion"
        assert page.locator("input#gpsIonZ").input_value() == "26"
        assert page.locator("input#gpsIonA").input_value() == "56"
        assert page.locator("input#gpsIonQ").input_value() == "2"
        assert page.locator("input#gpsIonE").input_value() == "10.5"

        # --- Verify console cleanliness ---
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
