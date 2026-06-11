import json
from unittest.mock import MagicMock, patch

import pytest

from app import (
    _automatic_visual_verification_args,
    app,
    dispatch_ai_tool,
)
from src.ai_tools import AI_GEOMETRY_TOOLS
from src.expression_evaluator import ExpressionEvaluator
from src.project_manager import ProjectManager


@pytest.fixture
def pm():
    manager = ProjectManager(ExpressionEvaluator())
    manager.create_empty_project()
    return manager


def _add_nested_sensitive_volume(pm):
    solid, error = pm.add_solid(
        "sensor_solid",
        "box",
        {"x": "4", "y": "6", "z": "8"},
    )
    assert error is None
    logical_volume, error = pm.add_logical_volume(
        "sensor_lv",
        solid["name"],
        "G4_Galactic",
        is_sensitive=True,
    )
    assert error is None
    placement, error = pm.add_physical_volume(
        "box_LV",
        "sensor_pv",
        logical_volume["name"],
        {"x": "5", "y": "0", "z": "0"},
        {"x": "0", "y": "0", "z": "0"},
        {"x": "1", "y": "1", "z": "1"},
    )
    assert error is None
    return placement


def test_inspect_geometry_focus_reports_ids_paths_bounds_and_detector_state(pm):
    parent = pm.current_geometry_state.logical_volumes["World"].content[0]
    success, update_payload = pm.update_physical_volume(
        parent.id,
        parent.name,
        {"x": "10", "y": "0", "z": "0"},
        None,
        None,
    )
    assert success is True
    assert "updated" in update_payload
    placement = _add_nested_sensitive_volume(pm)

    result = dispatch_ai_tool(pm, "inspect_geometry_focus", {
        "component_type": "physical_volume",
        "reference": placement["id"],
    })

    assert result["success"] is True
    inspection = result["inspection"]
    assert inspection["target"]["object_ids"] == [placement["id"]]
    assert inspection["target"]["ambiguous_reference"] is False
    assert inspection["solid_dimensions"] == [{
        "name": "sensor_solid",
        "type": "box",
        "raw_dimensions": {"x": "4", "y": "6", "z": "8"},
        "evaluated_dimensions": {"x": 4.0, "y": 6.0, "z": 8.0},
        "bounding_box_supported": True,
    }]
    assert inspection["logical_volume_state"][0]["material_ref"] == "G4_Galactic"
    assert inspection["logical_volume_state"][0]["is_sensitive"] is True

    instance = inspection["instances"][0]
    assert placement["id"] in instance["hierarchy_path"]
    assert parent.id in instance["hierarchy_path"]
    assert instance["local_transform"]["position_mm"]["x"] == pytest.approx(5.0)
    assert instance["world_transform"]["position_mm"]["x"] == pytest.approx(15.0)
    assert instance["world_bounding_box_mm"]["size"] == {
        "x": pytest.approx(4.0),
        "y": pytest.approx(6.0),
        "z": pytest.approx(8.0),
    }
    assert inspection["relationships"]["parents"][0]["canonical_id"] == parent.id


def test_inspect_geometry_focus_reports_nearby_overlap_concern(pm):
    first = _add_nested_sensitive_volume(pm)
    second, error = pm.add_physical_volume(
        "box_LV",
        "sensor_overlap_pv",
        "sensor_lv",
        {"x": "5", "y": "0", "z": "0"},
        {"x": "0", "y": "0", "z": "0"},
        {"x": "1", "y": "1", "z": "1"},
    )
    assert error is None

    inspection = pm.inspect_geometry_focus(
        "physical_volume",
        first["id"],
        nearby_limit=3,
    )

    nearby = inspection["relationships"]["nearby_components"]
    overlap_neighbor = next(
        item for item in nearby
        if item["canonical_id"] == second["id"]
    )
    assert overlap_neighbor["aabb_intersects"] is True
    concerns = inspection["geometry_concerns"]
    assert concerns["summary"]["has_overlap_or_containment_concerns"] is True
    assert "possible_overlap_aabb" in {
        issue["code"] for issue in concerns["issues"]
    }


def test_inspect_geometry_focus_bounds_asymmetric_polycone(pm):
    solid, error = pm.add_solid(
        "polycone_solid",
        "genericPolycone",
        {
            "startphi": "0",
            "deltaphi": "360*deg",
            "rzpoints": [
                {"r": "5", "z": "-10"},
                {"r": "20", "z": "30"},
            ],
        },
    )
    assert error is None
    logical_volume, error = pm.add_logical_volume(
        "polycone_lv",
        solid["name"],
        "G4_Galactic",
    )
    assert error is None
    placement, error = pm.add_physical_volume(
        "World",
        "polycone_pv",
        logical_volume["name"],
        {"x": "100", "y": "0", "z": "0"},
        {"x": "0", "y": "0", "z": "0"},
        {"x": "1", "y": "1", "z": "1"},
    )
    assert error is None

    inspection = pm.inspect_geometry_focus(
        "physical_volume",
        placement["id"],
    )

    bounds = inspection["instances"][0]["world_bounding_box_mm"]
    assert bounds["min"] == {
        "x": pytest.approx(80.0),
        "y": pytest.approx(-20.0),
        "z": pytest.approx(-10.0),
    }
    assert bounds["max"] == {
        "x": pytest.approx(120.0),
        "y": pytest.approx(20.0),
        "z": pytest.approx(30.0),
    }
    assert inspection["solid_dimensions"][0]["bounding_box_supported"] is True


def test_risk_policy_keeps_appearance_edit_receipt_only(pm):
    result = dispatch_ai_tool(pm, "set_volume_appearance", {
        "name": "box_LV",
        "color": "#336699",
        "opacity": 0.5,
    })

    assert result["success"] is True
    verification = result["risk_aware_verification"]
    assert verification["risk_level"] == "low"
    assert verification["policy"]["edit_receipt_only"] is True
    assert "focused_geometry_checks" not in verification


def test_risk_policy_focuses_single_spatial_edit(pm):
    placement = pm.current_geometry_state.logical_volumes["World"].content[0]

    result = dispatch_ai_tool(pm, "modify_physical_volume", {
        "pv_id": placement.id,
        "position": {"x": "12", "y": "-2", "z": "1"},
    })

    assert result["success"] is True
    verification = result["risk_aware_verification"]
    assert verification["risk_level"] == "spatial"
    assert verification["policy"]["focused_geometry_check"] is True
    assert verification["policy"]["visual_verification"] is False
    inspected_instance = verification["focused_geometry_checks"][0]["instances"][0]
    assert inspected_instance["canonical_id"] == placement.id
    assert inspected_instance["world_transform"]["position_mm"]["x"] == pytest.approx(12.0)


def test_risk_policy_escalates_multi_spatial_batch_without_duplicate_child_checks(pm):
    placement = pm.current_geometry_state.logical_volumes["World"].content[0]

    result = dispatch_ai_tool(pm, "batch_geometry_update", {
        "operations": [
            {
                "tool_name": "modify_solid",
                "arguments": {
                    "name": "box_solid",
                    "params": {"x": "80", "y": "70", "z": "60"},
                },
            },
            {
                "tool_name": "modify_physical_volume",
                "arguments": {
                    "pv_id": placement.id,
                    "position": {"x": "4", "y": "0", "z": "0"},
                },
            },
        ],
    })

    assert result["success"] is True
    assert all(
        "risk_aware_verification" not in child
        for child in result["batch_results"]
    )
    verification = result["risk_aware_verification"]
    assert verification["risk_level"] == "high_spatial"
    assert verification["scoped_overlap_checks"]
    assert verification["visual_verification"]["required"] is True
    assert _automatic_visual_verification_args(result)["views"] == [
        "isometric",
        "top",
        "side",
    ]


def test_inspection_tool_is_exposed_in_core_ai_catalog():
    tool = next(
        entry
        for entry in AI_GEOMETRY_TOOLS
        if entry["name"] == "inspect_geometry_focus"
    )

    assert tool["parameters"]["required"] == ["reference"]
    assert tool["parameters"]["properties"]["component_type"]["enum"] == [
        "auto",
        "solid",
        "logical_volume",
        "physical_volume",
    ]


def test_streamed_high_spatial_edit_automatically_requests_visual_capture(pm):
    placement = pm.current_geometry_state.logical_volumes["World"].content[0]
    batch_arguments = {
        "operations": [
            {
                "tool_name": "modify_solid",
                "arguments": {
                    "name": "box_solid",
                    "params": {"x": "75", "y": "70", "z": "65"},
                },
            },
            {
                "tool_name": "modify_physical_volume",
                "arguments": {
                    "pv_id": placement.id,
                    "position": {"x": "3", "y": "0", "z": "0"},
                },
            },
        ],
    }
    tool_response = MagicMock(
        backend_id="llama_cpp",
        model="qwen-local",
        text="",
        usage={},
        tool_calls=[],
        raw_response={
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "high-risk-batch",
                        "type": "function",
                        "function": {
                            "name": "batch_geometry_update",
                            "arguments": json.dumps(batch_arguments),
                        },
                    }],
                },
            }],
        },
    )
    final_response = MagicMock(
        backend_id="llama_cpp",
        model="qwen-local",
        text="The geometry was checked.",
        usage={},
        tool_calls=[],
        raw_response={
            "choices": [{
                "message": {
                    "content": "The geometry was checked.",
                    "tool_calls": [],
                },
            }],
        },
    )
    visual_request = {
        "request_id": "risk-visual-request",
        "tool_call_id": "high-risk-batch",
        "reason": "High spatial risk.",
        "questions": ["Check alignment."],
        "focus_component_ids": [placement.id],
        "capture_options": {
            "views": ["isometric", "top", "side"],
            "image_width": 768,
            "image_height": 576,
            "include_grid": True,
            "include_axes": True,
        },
    }
    visual_result = {
        "success": True,
        "request_id": "risk-visual-request",
        "reason": "High spatial risk.",
        "questions": ["Check alignment."],
        "focus_component_ids": [placement.id],
        "packet_metadata": {},
        "ai_attachments": [],
    }

    app.config["TESTING"] = True
    with (
        app.test_client() as client,
        patch("app.get_project_manager_for_session", return_value=pm),
        patch(
            "app.invoke_text_request_for_backend",
            side_effect=[tool_response, final_response],
        ),
        patch(
            "app._create_visual_verification_request",
            return_value=visual_request,
        ) as create_visual_request,
        patch(
            "app._wait_for_visual_verification_result",
            return_value=visual_result,
        ),
        patch("app.time.sleep"),
    ):
        response = client.post("/api/ai/chat/stream", json={
            "message": "Resize and move the selected detector.",
            "model": "llama_cpp::qwen-local",
            "execution_mode": "design_only",
        })
        stream_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '"type": "visual_verification_request"' in stream_text
    create_visual_request.assert_called_once()
    tool_entries = [
        entry
        for entry in pm.chat_history
        if entry.get("role") == "tool"
        and entry.get("name") == "batch_geometry_update"
    ]
    tool_result = json.loads(tool_entries[-1]["content"])
    assert tool_result["risk_aware_verification"]["visual_verification"][
        "status"
    ] == "completed"
