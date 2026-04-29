"""
Playwright test for AIRPET project save/load/reload workflow.

Verifies that a project containing a GPS source, a scoring mesh, and a
detector feature generator can be exported to JSON and reloaded while
preserving all three pieces of state.

Assumes the AIRPET dev server is running on http://localhost:5003.
Requires playwright (installed locally under .local-packages).
"""
import sys
import os
import socket
import tempfile

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
def test_project_save_load_reload_preserves_sources_scoring_and_generated_geometry():
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto("http://localhost:5003", wait_until="networkidle")

        # --- 1. Create a clean default geometry ---
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()
        page.wait_for_timeout(2000)

        # --- 2. Add a GPS source ---
        page.get_by_role("button", name="+ GPS").click()
        page.locator("input#gpsEditorName").fill("test_source")
        page.get_by_role("button", name="Create Source").click()
        page.wait_for_timeout(1000)

        # --- 3. Mark box_LV as sensitive ---
        page.get_by_role("button", name="Volumes").click()
        page.get_by_role("listitem").filter(has_text="box_LV").get_by_role("button", name="✏️").click()
        page.locator("input#lvEditorSensitive").check()
        page.locator("button#confirmLVEditor").click()
        page.wait_for_timeout(1000)

        # --- 4. Add a scoring mesh ---
        page.get_by_role("button", name="Properties").click()
        page.get_by_text("Scoring & Run Controls").first.click()
        page.get_by_role("button", name="Add Scoring Mesh").click()
        page.wait_for_timeout(1000)

        # --- 5. Create a detector feature generator (rectangular hole array) ---
        # The generator controls live in the Hierarchy tab
        page.get_by_role("button", name="Hierarchy").click()
        page.locator("button#toolsDropdownButton").click()
        page.locator("button#createDetectorFeatureGeneratorButton").click()
        page.wait_for_timeout(500)

        page.locator("input#detectorFeatureGeneratorName").fill("test_holes")
        # Ensure target solid is the default box
        target_select = page.locator("select#detectorFeatureGeneratorTargetSolid")
        if target_select.locator("option[value='box_solid']").count() > 0:
            target_select.select_option("box_solid")
        # Leave other defaults (3x3 holes, 5mm pitch, 2mm diameter, 5mm depth)
        page.locator("button#detectorFeatureGeneratorConfirm").click()
        page.wait_for_timeout(2000)

        # Verify generator appears before saving
        page.get_by_role("button", name="Properties").click()
        page.get_by_text("Detector Generators").first.click()
        assert page.locator("#detector_feature_generators_panel_root").get_by_text("test_holes").first.is_visible(), (
            "Expected detector generator 'test_holes' to be visible before save"
        )

        # --- 6. Save project JSON ---
        page.get_by_role("button", name="File").click()
        with page.expect_download() as download_info:
            page.locator("button#saveProjectButton").click()
        download = download_info.value

        with tempfile.TemporaryDirectory() as tmpdir:
            download_path = os.path.join(tmpdir, "project.json")
            download.save_as(download_path)

            # --- 7. Reload project JSON ---
            page.get_by_role("button", name="File").click()
            page.locator("input#projectFile").set_input_files(download_path)
            page.wait_for_timeout(3000)

            # --- 8. Verify state after reload ---
            # Hierarchy tab
            page.get_by_role("button", name="Hierarchy").click()
            assert page.get_by_text("World").first.is_visible(), "Expected 'World' in hierarchy after reload"
            assert page.get_by_text("box_PV (LV: box_LV)").first.is_visible(), (
                "Expected default box after reload"
            )
            assert page.get_by_text("test_source").first.is_visible(), (
                "Expected source 'test_source' after reload"
            )

            # Properties tab
            page.get_by_role("button", name="Properties").click()
            page.get_by_text("Scoring & Run Controls").first.click()
            assert page.locator("#scoring_panel_root").get_by_text("box_mesh_1").count() > 0, (
                "Expected scoring mesh 'box_mesh_1' in DOM after reload"
            )

            page.get_by_text("Detector Generators").first.click()
            assert page.locator("#detector_feature_generators_panel_root").get_by_text("test_holes").count() > 0, (
                "Expected generator 'test_holes' in DOM after reload"
            )

        # --- 9. Console cleanliness ---
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
