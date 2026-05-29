"""
Playwright smoke test for AIRPET Visual Verification Packet v1.

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
def test_visual_verification_packet_hook_captures_views_and_metadata():
    page_errors = []
    console_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("dialog", lambda dialog: dialog.accept())

        page.goto("http://localhost:5003", wait_until="networkidle")
        page.get_by_role("button", name="File").click()
        page.get_by_role("button", name="New Geometry").click()
        page.wait_for_function("window.airpetVisualVerification?.createPacket")
        page.locator("#viewer_container canvas").first.wait_for(state="visible")

        packet = page.evaluate(
            """async () => window.airpetVisualVerification.createPacket({
                views: ['front', 'top'],
                image_width: 320,
                image_height: 240,
            })"""
        )

        assert packet["kind"] == "airpet.visual_verification_packet"
        assert packet["schema_version"] == 1
        assert packet["capture"]["rendered_view_count"] == 2
        assert [view["name"] for view in packet["views"]] == ["front", "top"]
        assert all(view["image"]["data_url"].startswith("data:image/png;base64,") for view in packet["views"])
        assert all(view["image"]["width"] == 320 for view in packet["views"])
        assert packet["scene_summary"]["component_count"] >= 2
        assert packet["scene_summary"]["renderable_component_count"] >= 1
        assert any(component["name"] == "box_PV" for component in packet["components"])

        filtered_page_errors = [
            error for error in page_errors
            if "Password field is not contained in a form" not in error
        ]
        assert filtered_page_errors == []
        assert console_errors == []

        browser.close()
