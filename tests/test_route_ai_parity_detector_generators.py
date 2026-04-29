"""
Route-vs-AI parity test for detector feature generators.

Verifies that creating a detector feature generator through the direct
Flask route (/api/detector_feature_generators/upsert) and through the
AI tool dispatch (manage_detector_feature_generator) produce equivalent
geometry state for the same payload.

This protects the high-value tiled-sensor-array and boolean-cut workflows
that are already covered by Playwright (ACR-005).
"""

import json
import sys
import types
from unittest.mock import patch

import pytest

# Install OCC stubs before importing app (same pattern as test_detector_feature_generators_state)
class _DummyOccObject:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return self


def _install_occ_stubs():
    if "OCC" in sys.modules:
        return

    occ_module = types.ModuleType("OCC")
    occ_module.__path__ = []
    core_module = types.ModuleType("OCC.Core")
    core_module.__path__ = []

    sys.modules["OCC"] = occ_module
    sys.modules["OCC.Core"] = core_module

    module_specs = {
        "OCC.Core.STEPControl": {"STEPControl_Reader": _DummyOccObject},
        "OCC.Core.TopAbs": {
            "TopAbs_SOLID": 0,
            "TopAbs_FACE": 1,
            "TopAbs_REVERSED": 2,
        },
        "OCC.Core.TopExp": {"TopExp_Explorer": _DummyOccObject},
        "OCC.Core.BRep": {
            "BRep_Tool": type(
                "_BRepTool",
                (),
                {"Triangulation": staticmethod(lambda *args, **kwargs: None)},
            )
        },
        "OCC.Core.BRepMesh": {"BRepMesh_IncrementalMesh": _DummyOccObject},
        "OCC.Core.TopLoc": {"TopLoc_Location": _DummyOccObject},
        "OCC.Core.gp": {"gp_Trsf": _DummyOccObject},
        "OCC.Core.TDF": {"TDF_Label": _DummyOccObject, "TDF_LabelSequence": _DummyOccObject},
        "OCC.Core.XCAFDoc": {
            "XCAFDoc_DocumentTool": type(
                "_XCAFDocDocumentTool",
                (),
                {"ShapeTool": staticmethod(lambda *args, **kwargs: _DummyOccObject())},
            )
        },
        "OCC.Core.STEPCAFControl": {"STEPCAFControl_Reader": _DummyOccObject},
        "OCC.Core.TDocStd": {"TDocStd_Document": _DummyOccObject},
    }

    for module_name, attrs in module_specs.items():
        module = types.ModuleType(module_name)
        for attr_name, value in attrs.items():
            setattr(module, attr_name, value)
        sys.modules[module_name] = module


_install_occ_stubs()

from app import app, dispatch_ai_tool
from src.project_manager import ProjectManager
from src.expression_evaluator import ExpressionEvaluator


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _make_pm():
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()
    return pm


def _strip_id_from_refs(obj):
    """Recursively strip 'id' keys from object refs so comparisons focus on names."""
    if isinstance(obj, dict):
        return {k: _strip_id_from_refs(v) for k, v in obj.items() if k != "id"}
    if isinstance(obj, list):
        return [_strip_id_from_refs(item) for item in obj]
    return obj


def _extract_relevant_state(pm):
    """Return a stable dict of generator and geometry state for comparison."""
    state = pm.current_geometry_state
    gens = state.detector_feature_generators

    def _normalize_obj_refs(refs):
        if not refs:
            return []
        return sorted([r["name"] for r in refs])

    generator_summaries = []
    for g in gens:
        gen = dict(g)
        # Remove volatile IDs for stable comparison
        gen.pop("generator_id", None)
        # Normalize target refs (AI path may add 'id' to refs; route path may not)
        gen["target"] = _strip_id_from_refs(gen.get("target", {}))
        realization = gen.get("realization", {})
        realization.pop("result_solid_ref", None)
        generated = realization.get("generated_object_refs", {})
        generated["solid_refs"] = _normalize_obj_refs(generated.get("solid_refs"))
        generated["logical_volume_refs"] = _normalize_obj_refs(
            generated.get("logical_volume_refs")
        )
        generated["placement_refs"] = _normalize_obj_refs(
            generated.get("placement_refs")
        )
        generator_summaries.append(gen)

    # Sort by generator name for stable comparison
    generator_summaries.sort(key=lambda x: x.get("name", ""))

    solids = {name: {"type": s.type} for name, s in sorted(state.solids.items())}
    lvs = {
        name: {"solid_ref": lv.solid_ref, "is_sensitive": lv.is_sensitive}
        for name, lv in sorted(state.logical_volumes.items())
    }
    pvs = []
    for lv in state.logical_volumes.values():
        if lv.content_type == "physvol":
            for pv in lv.content:
                pvs.append({"name": pv.name, "parent": lv.name, "placed": pv.volume_ref})
    pvs.sort(key=lambda x: x["name"])

    return {
        "generators": generator_summaries,
        "solids": solids,
        "logical_volumes": lvs,
        "placements": pvs,
    }


def test_route_vs_ai_parity_tiled_sensor_array(client):
    """
    Direct route and AI tool dispatch should produce the same tiled sensor array.
    """
    pm_route = _make_pm()
    pm_ai = _make_pm()

    route_payload = {
        "generator_type": "tiled_sensor_array",
        "name": "parity_sensor_array",
        "target": {"parent_logical_volume_ref": {"name": "World"}},
        "array": {"count_x": 2, "count_y": 2},
        "sensor": {"size_mm": {"x": 5, "y": 5}, "thickness_mm": 1.0, "material": "G4_Si"},
        "realize_now": True,
    }

    ai_tool_args = {
        "generator_type": "tiled_sensor_array",
        "name": "parity_sensor_array",
        "target": "World",
        "array": {"count_x": 2, "count_y": 2},
        "sensor": {"size_mm": {"x": 5, "y": 5}, "thickness_mm": 1.0, "material": "G4_Si"},
        "realize_now": True,
    }

    # --- Direct route path ---
    with patch("app.get_project_manager_for_session", return_value=pm_route):
        resp = client.post(
            "/api/detector_feature_generators/upsert",
            data=json.dumps(route_payload),
            content_type="application/json",
        )
    assert resp.status_code == 200
    route_body = resp.get_json()
    assert route_body["success"] is True

    # --- AI tool dispatch path ---
    ai_result = dispatch_ai_tool(pm_ai, "manage_detector_feature_generator", ai_tool_args)
    assert ai_result["success"] is True, ai_result.get("error")

    # --- Parity comparison ---
    route_state = _extract_relevant_state(pm_route)
    ai_state = _extract_relevant_state(pm_ai)

    assert route_state["generators"] == ai_state["generators"]
    assert route_state["solids"] == ai_state["solids"]
    assert route_state["logical_volumes"] == ai_state["logical_volumes"]
    assert route_state["placements"] == ai_state["placements"]


def test_route_vs_ai_parity_channel_cut_array(client):
    """
    Direct route and AI tool dispatch should produce the same channel cut array.
    This exercises the boolean-subtraction realization path.
    """
    pm_route = _make_pm()
    pm_ai = _make_pm()

    # Set up a target solid for the channel cut
    for pm in (pm_route, pm_ai):
        pm.add_solid("channel_block", "box", {"x": "20", "y": "20", "z": "10"})
        pm.add_logical_volume("channel_lv", "channel_block", "G4_Galactic")
        pm.add_physical_volume(
            "World",
            "channel_pv",
            "channel_lv",
            {"x": "0", "y": "0", "z": "0"},
            {"x": "0", "y": "0", "z": "0"},
            {"x": "1", "y": "1", "z": "1"},
        )

    route_payload = {
        "generator_type": "channel_cut_array",
        "name": "parity_channels",
        "target": {"solid_ref": {"name": "channel_block"}},
        "array": {"count": 2, "linear_pitch_mm": 6.0, "axis": "x"},
        "channel": {"width_mm": 2.0, "depth_mm": 5.0},
        "realize_now": True,
    }

    ai_tool_args = {
        "generator_type": "channel_cut_array",
        "name": "parity_channels",
        "target": "channel_block",
        "array": {"count": 2, "linear_pitch_mm": 6.0, "axis": "x"},
        "channel": {"width_mm": 2.0, "depth_mm": 5.0},
        "realize_now": True,
    }

    # --- Direct route path ---
    with patch("app.get_project_manager_for_session", return_value=pm_route):
        resp = client.post(
            "/api/detector_feature_generators/upsert",
            data=json.dumps(route_payload),
            content_type="application/json",
        )
    assert resp.status_code == 200
    route_body = resp.get_json()
    assert route_body["success"] is True

    # --- AI tool dispatch path ---
    ai_result = dispatch_ai_tool(pm_ai, "manage_detector_feature_generator", ai_tool_args)
    assert ai_result["success"] is True, ai_result.get("error")

    # --- Parity comparison ---
    route_state = _extract_relevant_state(pm_route)
    ai_state = _extract_relevant_state(pm_ai)

    assert route_state["generators"] == ai_state["generators"]
    assert route_state["solids"] == ai_state["solids"]
    assert route_state["logical_volumes"] == ai_state["logical_volumes"]
    assert route_state["placements"] == ai_state["placements"]
