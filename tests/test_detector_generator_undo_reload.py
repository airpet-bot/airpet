"""
Playwright test for AIRPET detector generator create/undo/reload workflow.

Creates a tiled sensor array generator and a channel cut array (boolean-cut)
generator, verifies they appear in the hierarchy, solids panel, and detector
generators panel, undoes the channel cut creation, verifies stale-object cleanup,
reloads the page, and confirms the tiled sensor array persists with zero uncaught
JavaScript errors.

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
def test_detector_generator_create_undo_reload_tiled_sensor_and_boolean_cut():
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
        page.locator("#newProjectButton").click(force=True)
        page.wait_for_timeout(2000)

        # --- 2. Create a tiled sensor array generator ---
        page.get_by_role("button", name="Hierarchy").click()
        page.locator("#toolsDropdownButton").click()
        page.locator("#createDetectorFeatureGeneratorButton").click()
        page.wait_for_timeout(500)

        page.locator("#detectorFeatureGeneratorType").select_option("tiled_sensor_array")
        page.wait_for_timeout(300)

        page.locator("#detectorFeatureGeneratorName").fill("test_sensor_array")
        page.locator("#detectorFeatureGeneratorTargetSolid").select_option("World")
        page.locator("#detectorFeatureGeneratorCountX").fill("2")
        page.locator("#detectorFeatureGeneratorCountY").fill("2")
        page.locator("#detectorFeatureGeneratorConfirm").click()
        page.wait_for_timeout(2000)

        # --- 3. Create a channel cut array (boolean-cut) generator ---
        page.locator("#toolsDropdownButton").click()
        page.wait_for_timeout(300)
        page.locator("#createDetectorFeatureGeneratorButton").click()
        page.wait_for_timeout(500)

        page.locator("#detectorFeatureGeneratorType").select_option("channel_cut_array")
        page.wait_for_timeout(300)

        page.locator("#detectorFeatureGeneratorName").fill("test_channels")
        page.locator("#detectorFeatureGeneratorTargetSolid").select_option("box_solid")
        page.locator("#detectorFeatureGeneratorLinearCount").fill("2")
        page.locator("#detectorFeatureGeneratorChannelWidth").fill("1")
        page.locator("#detectorFeatureGeneratorChannelDepth").fill("2")
        page.locator("#detectorFeatureGeneratorConfirm").click()
        page.wait_for_timeout(2000)

        # --- 4. Verify both generators appear in panels ---
        # Hierarchy: tiled sensor array placements should be visible
        page.get_by_role("button", name="Hierarchy").click()
        assert page.get_by_text("test_sensor_array__sensor_r1_c1_pv").first.is_visible(), (
            "Expected tiled sensor placement in hierarchy"
        )
        assert page.get_by_text("box_PV (LV: box_LV)").first.is_visible(), (
            "Expected box_PV in hierarchy"
        )

        # Solids panel: boolean result and cutter should exist
        page.get_by_role("button", name="Solids").click()
        solids_root = page.locator("#solids_list_root")
        assert solids_root.get_by_text("test_channels__result").count() > 0, (
            "Expected channel cut result solid in solids panel"
        )
        assert solids_root.get_by_text("test_channels__channel_cutter").count() > 0, (
            "Expected channel cut cutter solid in solids panel"
        )
        assert solids_root.get_by_text("test_sensor_array__sensor_solid").count() > 0, (
            "Expected tiled sensor solid in solids panel"
        )

        # Detector Generators panel: both should be listed
        page.get_by_role("button", name="Properties").click()
        page.get_by_text("Detector Generators").first.click()
        gen_root = page.locator("#detector_feature_generators_panel_root")
        assert gen_root.get_by_text("test_sensor_array").count() > 0, (
            "Expected tiled sensor generator in generators panel"
        )
        assert gen_root.get_by_text("test_channels").count() > 0, (
            "Expected channel cut generator in generators panel"
        )

        # --- 5. Undo the channel cut generator creation ---
        page.get_by_role("button", name="Edit", exact=True).click()
        page.wait_for_timeout(300)
        page.locator("#undoButton").click()
        page.wait_for_timeout(2000)

        # --- 6. Verify stale-object cleanup after undo ---
        # Channel cut generator should be gone
        page.get_by_role("button", name="Properties").click()
        page.get_by_text("Detector Generators").first.click()
        gen_root = page.locator("#detector_feature_generators_panel_root")
        assert gen_root.get_by_text("test_channels").count() == 0, (
            "Expected channel cut generator to be removed after undo"
        )
        assert gen_root.get_by_text("test_sensor_array").count() > 0, (
            "Expected tiled sensor generator to persist after undo"
        )

        # Solids panel: boolean solids should be cleaned up, box_solid restored
        page.get_by_role("button", name="Solids").click()
        solids_root = page.locator("#solids_list_root")
        assert solids_root.get_by_text("test_channels__result").count() == 0, (
            "Expected channel cut result solid to be removed after undo (stale-object cleanup)"
        )
        assert solids_root.get_by_text("test_channels__channel_cutter").count() == 0, (
            "Expected channel cut cutter solid to be removed after undo (stale-object cleanup)"
        )
        assert solids_root.get_by_text("box_solid").count() > 0, (
            "Expected original box_solid to be restored after undo"
        )
        assert solids_root.get_by_text("test_sensor_array__sensor_solid").count() > 0, (
            "Expected tiled sensor solid to persist after undo"
        )

        # Hierarchy: tiled sensor placements should still be present
        page.get_by_role("button", name="Hierarchy").click()
        assert page.get_by_text("test_sensor_array__sensor_r1_c1_pv").first.is_visible(), (
            "Expected tiled sensor placement to persist after undo"
        )

        # --- 7. Reload the page and verify persistence ---
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Hierarchy after reload
        page.get_by_role("button", name="Hierarchy").click()
        assert page.get_by_text("World").first.is_visible(), "Expected 'World' after reload"
        assert page.get_by_text("box_PV (LV: box_LV)").first.is_visible(), (
            "Expected box_PV after reload"
        )
        assert page.get_by_text("test_sensor_array__sensor_r1_c1_pv").first.is_visible(), (
            "Expected tiled sensor placement after reload"
        )

        # Solids after reload
        page.get_by_role("button", name="Solids").click()
        solids_root = page.locator("#solids_list_root")
        assert solids_root.get_by_text("box_solid").count() > 0, "Expected box_solid after reload"
        assert solids_root.get_by_text("test_sensor_array__sensor_solid").count() > 0, (
            "Expected tiled sensor solid after reload"
        )
        assert solids_root.get_by_text("test_channels__result").count() == 0, (
            "Expected no stale channel cut result solid after reload"
        )
        assert solids_root.get_by_text("test_channels__channel_cutter").count() == 0, (
            "Expected no stale channel cut cutter solid after reload"
        )

        # Generators after reload
        page.get_by_role("button", name="Properties").click()
        page.get_by_text("Detector Generators").first.click()
        gen_root = page.locator("#detector_feature_generators_panel_root")
        assert gen_root.get_by_text("test_sensor_array").count() > 0, (
            "Expected tiled sensor generator after reload"
        )
        assert gen_root.get_by_text("test_channels").count() == 0, (
            "Expected no channel cut generator after reload"
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
