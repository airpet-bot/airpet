from unittest.mock import MagicMock, patch

import pytest

from app import (
    _format_ai_selection_context,
    _resolve_ai_selection_context,
    app,
    dispatch_ai_tool,
)
from src.expression_evaluator import ExpressionEvaluator
from src.project_manager import ProjectManager


@pytest.fixture
def pm():
    manager = ProjectManager(ExpressionEvaluator())
    manager.create_empty_project()
    return manager


def test_selection_context_resolves_live_full_id_and_ignores_stale_items(pm):
    target_pv = pm.current_geometry_state.logical_volumes["World"].content[0]

    selection = _resolve_ai_selection_context(pm, [
        {
            "component_type": "physical_volume",
            "id": target_pv.id,
            "name": "Misleading browser label",
        },
        {
            "component_type": "physical_volume",
            "id": "stale-pv-id",
            "name": "DeletedPV",
        },
        {
            "component_type": "unsupported",
            "id": "ignored",
        },
    ])

    assert len(selection) == 1
    selected = selection[0]
    assert selected["tool_reference"] == target_pv.id
    assert selected["name"] == target_pv.name
    assert selected["details"]["volume_ref"] == "box_LV"
    assert selected["details"]["parent_lv_name"] == "World"
    assert target_pv.id in _format_ai_selection_context(selection)


def test_stream_chat_includes_only_resolved_selection_in_model_context(pm):
    target_pv = pm.current_geometry_state.logical_volumes["World"].content[0]
    app.config["TESTING"] = True

    with (
        app.test_client() as client,
        patch("app.get_project_manager_for_session", return_value=pm),
        patch("app.invoke_text_request_for_backend") as invoke_adapter,
    ):
        invoke_adapter.return_value = MagicMock(
            backend_id="llama_cpp",
            model="qwen-local",
            text="I found the selected placement.",
            usage={},
            raw_response={},
        )
        response = client.post("/api/ai/chat/stream", json={
            "message": "Move this part.",
            "model": "llama_cpp::qwen-local",
            "execution_mode": "design_only",
            "selection_context": [
                {
                    "component_type": "physical_volume",
                    "id": target_pv.id,
                    "name": "Browser label",
                },
                {
                    "component_type": "physical_volume",
                    "id": "stale-pv-id",
                    "name": "Stale browser item",
                },
            ],
        })
        response.get_data(as_text=True)
        request_payload = invoke_adapter.call_args.args[1]

    assert response.status_code == 200
    model_context = request_payload.messages[-1].content
    assert "Current AIRPET UI Selection" in model_context
    assert target_pv.id in model_context
    assert target_pv.name in model_context
    assert "stale-pv-id" not in model_context
    assert "Browser label" not in model_context


def test_modify_physical_volume_returns_verified_before_after_receipt(pm):
    target_pv = pm.current_geometry_state.logical_volumes["World"].content[0]

    result = dispatch_ai_tool(pm, "modify_physical_volume", {
        "pv_id": target_pv.id,
        "position": {"x": "12", "y": "-3", "z": "5"},
        "rotation": {"x": "0", "y": "0", "z": "45*deg"},
    })

    assert result["success"] is True
    receipt = result["edit_receipt"]
    assert receipt["verified"] is True
    assert receipt["outcome"] == "changed"
    assert receipt["target"] == {
        "component_type": "physical_volume",
        "tool_reference": target_pv.id,
    }
    assert receipt["before"]["position"] == {"x": "0", "y": "0", "z": "0"}
    assert receipt["after"]["position"] == {
        "x": "12",
        "y": "-3",
        "z": "5",
    }
    assert receipt["after"]["rotation"]["z"] == "45*deg"
    assert "position" in receipt["changed_fields"]
    assert "_evaluated_position" in receipt["changed_fields"]


def test_modify_solid_receipt_reports_applied_dimensions(pm):
    result = dispatch_ai_tool(pm, "modify_solid", {
        "name": "box_solid",
        "params": {"x": "60", "y": "70", "z": "8"},
    })

    assert result["success"] is True
    receipt = result["edit_receipt"]
    assert receipt["verified"] is True
    assert receipt["after"]["raw_parameters"] == {
        "x": "60",
        "y": "70",
        "z": "8",
    }
    assert receipt["after"]["_evaluated_parameters"] == {
        "x": 60.0,
        "y": 70.0,
        "z": 8.0,
    }


def test_update_property_receipt_verifies_exact_nested_field(pm):
    result = dispatch_ai_tool(pm, "update_property", {
        "object_type": "environment",
        "object_id": "global_uniform_magnetic_field",
        "property_path": "field_vector_tesla.y",
        "new_value": "1.5",
    })

    assert result["success"] is True
    receipt = result["edit_receipt"]
    assert receipt["verified"] is True
    assert receipt["before"]["field_vector_tesla.y"] == 0.0
    assert receipt["after"]["field_vector_tesla.y"] == 1.5
    assert receipt["changed_fields"] == ["field_vector_tesla.y"]


def test_detector_readout_receipt_verifies_persisted_signal_policy(pm):
    result = dispatch_ai_tool(pm, "configure_detector_readout", {
        "hit_selection_mode": "target_hits_only",
        "target_logical_volumes": ["box_LV"],
        "minimum_hit_count": 2,
        "hit_energy_threshold": "25 keV",
    })

    assert result["success"] is True
    receipt = result["edit_receipt"]
    assert receipt["verified"] is True
    assert receipt["after"]["hit_selection_mode"] == "target_hits_only"
    assert receipt["after"]["hit_target_logical_volumes"] == ["box_LV"]
    assert receipt["after"]["hit_minimum_multiplicity"] == 2
    assert receipt["after"]["hit_energy_threshold"] == "25 keV"


def test_batch_geometry_update_keeps_receipt_for_each_edit(pm):
    target_pv = pm.current_geometry_state.logical_volumes["World"].content[0]

    result = dispatch_ai_tool(pm, "batch_geometry_update", {
        "operations": [
            {
                "tool_name": "modify_solid",
                "arguments": {
                    "name": "box_solid",
                    "params": {"x": "40", "y": "40", "z": "4"},
                },
            },
            {
                "tool_name": "modify_physical_volume",
                "arguments": {
                    "pv_id": target_pv.id,
                    "position": {"x": "1", "y": "2", "z": "3"},
                },
            },
        ],
    })

    assert result["success"] is True
    assert [
        item["edit_receipt"]["target"]["component_type"]
        for item in result["batch_results"]
    ] == ["solid", "physical_volume"]
