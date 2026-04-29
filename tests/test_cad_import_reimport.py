"""
Playwright test for AIRPET CAD import/reimport browser workflow.

Verifies that a STEP file can be imported via the UI, that the CAD Imports
panel appears and shows the provenance record, and that a revised STEP file
can be reimported in-place without errors.

Assumes the AIRPET dev server is running on http://localhost:5003.
Requires playwright (installed locally under .local-packages).
"""
import sys
import os
import socket

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
def test_cad_import_reimport_workflow():
    page_errors = []
    console_errors = []

    step_fixture_dir = os.path.join(
        os.path.dirname(__file__), "fixtures", "step", "corpus"
    )
    base_step_path = os.path.join(step_fixture_dir, "test_box.step")
    revised_step_path = os.path.join(step_fixture_dir, "test_box_revised.step")

    assert os.path.exists(base_step_path), f"Missing fixture: {base_step_path}"
    assert os.path.exists(revised_step_path), f"Missing fixture: {revised_step_path}"

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

        # --- 2. Verify CAD Imports accordion is hidden before any import ---
        page.get_by_role("button", name="Properties").click()
        cad_accordion = page.locator("#cad_imports_panel_root").locator("xpath=../..")
        assert not cad_accordion.is_visible(), "CAD Imports accordion should be hidden before import"

        # --- 3. Import base STEP file ---
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="Import CAD (STEP)...").click()
        page.locator("input#stepFile").set_input_files(base_step_path)

        # Wait for the import modal and confirm
        page.wait_for_selector("#stepImportModal", state="visible")
        assert page.locator("#stepFileName").text_content() == "test_box.step"
        page.locator("button#confirmStepImport").click()

        # Wait for import to complete and loading to disappear
        page.wait_for_timeout(3000)

        # Dismiss the Smart CAD report modal if it appears
        report_modal = page.locator("#stepImportReportModal")
        if report_modal.is_visible():
            page.locator("#closeStepImportReport").click()
            page.wait_for_timeout(500)

        # --- 4. Verify CAD Imports panel appears and shows the record ---
        page.get_by_role("button", name="Properties").click()
        page.wait_for_timeout(500)

        assert cad_accordion.is_visible(), "CAD Imports accordion should be visible after import"
        # Expand the accordion if needed
        cad_header = cad_accordion.locator(".accordion-header")
        if not cad_accordion.locator(".accordion-content").is_visible():
            cad_header.click()
            page.wait_for_timeout(500)

        panel = page.locator("#cad_imports_panel_root")
        assert panel.get_by_text("test_box.step").first.is_visible(), (
            "Expected CAD import record for 'test_box.step' to be visible"
        )
        assert panel.get_by_text("Reimport STEP...").first.is_visible(), (
            "Expected 'Reimport STEP...' button to be visible"
        )

        # --- 5. Reimport revised STEP file via the panel ---
        # The panel creates a hidden file input dynamically
        reimport_input = panel.locator("input[type='file']")
        assert reimport_input.count() > 0, "Expected hidden file input for reimport"
        reimport_input.set_input_files(revised_step_path)

        # Wait for reimport modal
        page.wait_for_selector("#stepImportModal", state="visible")
        # Modal title should reflect reimport context
        assert "Reimport" in page.locator("#stepImportModalTitle").text_content(), (
            "Expected modal title to indicate reimport"
        )
        page.locator("button#confirmStepImport").click()

        # Wait for reimport to complete
        page.wait_for_timeout(3000)

        # Dismiss report modal if present
        if report_modal.is_visible():
            page.locator("#closeStepImportReport").click()
            page.wait_for_timeout(500)

        # --- 6. Verify panel still shows one record with revised filename ---
        page.get_by_role("button", name="Properties").click()
        page.wait_for_timeout(500)

        if not cad_accordion.locator(".accordion-content").is_visible():
            cad_header.click()
            page.wait_for_timeout(500)

        assert panel.get_by_text("test_box_revised.step").first.is_visible(), (
            "Expected CAD import record to show revised filename after reimport"
        )

        # --- 7. Verify sidebar is still functional (other accordions accessible) ---
        # Click Detector Generators accordion to ensure narrow sidebar isn't broken
        dg_accordion = page.locator("#detector_feature_generators_panel_root").locator("xpath=../..")
        dg_header = dg_accordion.locator(".accordion-header")
        dg_header.click()
        page.wait_for_timeout(500)
        assert dg_accordion.locator(".accordion-content").is_visible(), (
            "Detector Generators accordion should still be functional after CAD import"
        )

        scoring_accordion = page.locator("#scoring_panel_root").locator("xpath=../..")
        scoring_header = scoring_accordion.locator(".accordion-header")
        scoring_header.click()
        page.wait_for_timeout(500)
        assert scoring_accordion.locator(".accordion-content").is_visible(), (
            "Scoring accordion should still be functional after CAD import"
        )

        # --- 8. Console cleanliness ---
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
