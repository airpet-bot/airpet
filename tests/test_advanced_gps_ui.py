"""
Playwright smoke test for the Advanced GPS source editor panel.

Assumes the AIRPET dev server is running on http://localhost:5003.
Requires playwright (installed locally under .local-packages).
"""
import os
import socket
import sys

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
def test_advanced_gps_editor_creates_and_round_trips_source():
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        page.goto("http://localhost:5003", wait_until="networkidle")
        page.on("dialog", lambda dialog: dialog.accept())

        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()
        page.wait_for_timeout(1500)

        page.get_by_role("button", name="+ GPS").click()
        page.locator("#gpsEditorName").fill("advanced_gps_ui_source")
        page.locator("#gpsAdvancedGpsPanel summary").click()
        page.locator("#gpsAdvancedGpsEnabled").check()

        page.locator("#gpsAdvanced_airpet_transform_mode").select_option("structured")
        page.locator("#gpsAdvanced_source_list_multiple_vertex").select_option("true")
        page.locator("#gpsAdvanced_control_time").fill("2 ns")
        page.locator("#gpsAdvanced_control_checkVolume").select_option("false")
        page.locator("#gpsAdvanced_position_pos_type").select_option("Beam")
        page.locator("#gpsAdvanced_position_pos_centre").fill("0 0 5 mm")
        page.locator("#gpsAdvanced_angular_ang_type").select_option("focused")
        page.locator("#gpsAdvanced_angular_ang_focuspoint").fill("0 0 100 mm")
        page.locator("#gpsAdvanced_energy_ene_type").select_option("Arb")
        page.locator("#gpsAdvanced_energy_ene_applyEneWeight").select_option("true")

        page.get_by_role("button", name="Add Histogram").click()
        hist_row = page.locator('[data-gps-advanced-histogram-row="true"]').first
        hist_row.locator('[data-gps-advanced-histogram-field="type"]').select_option("energy")
        hist_row.locator('[data-gps-advanced-histogram-field="reset"]').check()
        hist_row.locator('[data-gps-advanced-histogram-field="points"]').fill("1 keV 0.2\n10 keV 1.0")
        hist_row.locator('[data-gps-advanced-histogram-field="interpolation"]').select_option("Lin")

        page.get_by_role("button", name="Add Command").click()
        cmd_row = page.locator('[data-gps-command-sequence-row="true"]').first
        cmd_row.locator('[data-gps-command-sequence-field="command"]').fill("hist/point")
        cmd_row.locator('[data-gps-command-sequence-field="value"]').fill("20 keV 0.5")

        page.get_by_role("button", name="Create Source").click()
        page.wait_for_timeout(1000)

        assert page.get_by_text("advanced_gps_ui_source").first.is_visible()
        page.get_by_text("advanced_gps_ui_source").first.click()
        page.wait_for_timeout(400)
        assert "control" in page.locator('label:has-text("Advanced GPS:") + span').inner_text()
        assert page.locator('label:has-text("GPS Transform Mode:") + span').inner_text() == "structured"

        page.get_by_text("advanced_gps_ui_source").first.dblclick()
        page.wait_for_timeout(500)
        assert page.locator("#gpsAdvancedGpsEnabled").is_checked()
        assert page.locator("#gpsAdvanced_airpet_transform_mode").input_value() == "structured"
        assert page.locator("#gpsAdvanced_position_pos_centre").input_value() == "0 0 5 mm"
        assert page.locator("#gpsAdvanced_energy_ene_applyEneWeight").input_value() == "true"
        assert page.locator('[data-gps-advanced-histogram-row="true"]').count() == 1
        assert page.locator('[data-gps-command-sequence-row="true"]').count() == 1

        assert page_errors == []
        assert console_errors == []
        browser.close()

