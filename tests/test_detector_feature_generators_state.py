import json
import sys
import types

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import GeometryState


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

from src.project_manager import ProjectManager


def _make_pm():
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()
    return pm


def _normalize_detector_feature_generators(raw_generators):
    return GeometryState.from_dict(
        {"detector_feature_generators": raw_generators}
    ).detector_feature_generators


def test_detector_feature_generator_contract_defaults_and_invalid_entries():
    state = GeometryState()
    assert state.detector_feature_generators == []
    assert state.to_dict()["detector_feature_generators"] == []

    loaded = GeometryState.from_dict(
        {
            "detector_feature_generators": [
                {
                    "generator_type": "rectangular_drilled_hole_array",
                    "target": {
                        "solid_ref": {"name": "collimator_block"},
                    },
                    "pattern": {
                        "count_x": "4",
                        "count_y": 3,
                        "pitch_mm": {"x": "7.5", "y": 6},
                    },
                    "hole": {
                        "diameter_mm": "1.5",
                        "depth_mm": 8,
                    },
                },
                {
                    "generator_id": "invalid-negative-count",
                    "generator_type": "rectangular_drilled_hole_array",
                    "target": {
                        "solid_ref": {"name": "ignored_block"},
                    },
                    "pattern": {
                        "count_x": 0,
                        "count_y": 1,
                        "pitch_mm": {"x": 5, "y": 5},
                    },
                    "hole": {
                        "diameter_mm": 1.0,
                        "depth_mm": 2.0,
                    },
                },
                {
                    "generator_id": "unsupported-kind",
                    "generator_type": "spiral_drilled_hole_array",
                    "target": {
                        "solid_ref": {"name": "ignored_block"},
                    },
                    "pattern": {
                        "count_x": 1,
                        "count_y": 1,
                        "pitch_mm": {"x": 5, "y": 5},
                    },
                    "hole": {
                        "diameter_mm": 1.0,
                        "depth_mm": 2.0,
                    },
                },
            ]
        }
    )

    assert len(loaded.detector_feature_generators) == 1
    entry = loaded.detector_feature_generators[0]
    assert entry["generator_id"].startswith("detector_feature_generator_")
    assert entry["name"].startswith("rectangular_drilled_hole_array_")
    assert entry["schema_version"] == 1
    assert entry["generator_type"] == "rectangular_drilled_hole_array"
    assert entry["enabled"] is True
    assert entry["target"] == {
        "solid_ref": {"name": "collimator_block"},
        "logical_volume_refs": [],
    }
    assert entry["pattern"] == {
        "count_x": 4,
        "count_y": 3,
        "pitch_mm": {"x": 7.5, "y": 6.0},
        "origin_offset_mm": {"x": 0.0, "y": 0.0},
        "anchor": "target_center",
    }
    assert entry["hole"] == {
        "shape": "cylindrical",
        "diameter_mm": 1.5,
        "depth_mm": 8.0,
        "axis": "z",
        "drill_from": "positive_z_face",
    }
    assert entry["realization"] == {
        "mode": "boolean_subtraction",
        "status": "spec_only",
        "result_solid_ref": None,
        "generated_object_refs": {
            "solid_refs": [],
            "logical_volume_refs": [],
            "placement_refs": [],
        },
    }


def test_circular_detector_feature_generator_contract_defaults():
    loaded = GeometryState.from_dict(
        {
            "detector_feature_generators": [
                {
                    "generator_type": "circular_drilled_hole_array",
                    "target": {
                        "solid_ref": {"name": "circular_collimator_block"},
                    },
                    "pattern": {
                        "hole_count": "6",
                        "radius_mm": "12.5",
                        "orientation_deg": "15",
                        "origin_offset_mm": {"x": "1.5", "y": -2},
                    },
                    "hole": {
                        "diameter_mm": "2.5",
                        "depth_mm": 7,
                    },
                },
            ]
        }
    )

    assert len(loaded.detector_feature_generators) == 1
    entry = loaded.detector_feature_generators[0]
    assert entry["generator_id"].startswith("detector_feature_generator_")
    assert entry["name"].startswith("circular_drilled_hole_array_")
    assert entry["generator_type"] == "circular_drilled_hole_array"
    assert entry["target"] == {
        "solid_ref": {"name": "circular_collimator_block"},
        "logical_volume_refs": [],
    }
    assert entry["pattern"] == {
        "count": 6,
        "radius_mm": 12.5,
        "orientation_deg": 15.0,
        "origin_offset_mm": {"x": 1.5, "y": -2.0},
        "anchor": "target_center",
    }
    assert entry["hole"] == {
        "shape": "cylindrical",
        "diameter_mm": 2.5,
        "depth_mm": 7.0,
        "axis": "z",
        "drill_from": "positive_z_face",
    }


def test_detector_feature_generator_contract_roundtrips_through_project_manager():
    valid_payload = {
        "generator_id": "dfg_rect_holes_fixture",
        "name": "fixture_collimator_holes",
        "schema_version": 1,
        "generator_type": "rectangular_drilled_hole_array",
        "enabled": True,
        "target": {
            "solid_ref": {"id": "solid-target-1", "name": "collimator_block"},
            "logical_volume_refs": [
                {"id": "lv-target-1", "name": "collimator_lv"},
                {"id": "lv-target-1", "name": "collimator_lv"},
            ],
        },
        "pattern": {
            "count_x": 5,
            "count_y": 4,
            "pitch_mm": {"x": 7.5, "y": 9.25},
            "origin_offset_mm": {"x": 1.25, "y": -2.5},
            "anchor": "target_center",
        },
        "hole": {
            "shape": "cylindrical",
            "diameter_mm": 2.0,
            "depth_mm": 12.5,
            "axis": "z",
            "drill_from": "positive_z_face",
        },
        "realization": {
            "mode": "boolean_subtraction",
            "status": "generated",
            "result_solid_ref": {"id": "solid-result-1", "name": "collimator_block_drilled"},
            "generated_object_refs": {
                "solid_refs": [
                    {"id": "solid-result-1", "name": "collimator_block_drilled"},
                    {"id": "solid-cutter-1", "name": "collimator_hole_cutter"},
                ],
                "logical_volume_refs": [
                    {"id": "lv-target-1", "name": "collimator_lv"},
                ],
                "placement_refs": [
                    {"id": "pv-target-1", "name": "collimator_pv"},
                ],
            },
        },
    }

    expected_payload = {
        "generator_id": "dfg_rect_holes_fixture",
        "name": "fixture_collimator_holes",
        "schema_version": 1,
        "generator_type": "rectangular_drilled_hole_array",
        "enabled": True,
        "target": {
            "solid_ref": {"id": "solid-target-1", "name": "collimator_block"},
            "logical_volume_refs": [
                {"id": "lv-target-1", "name": "collimator_lv"},
            ],
        },
        "pattern": {
            "count_x": 5,
            "count_y": 4,
            "pitch_mm": {"x": 7.5, "y": 9.25},
            "origin_offset_mm": {"x": 1.25, "y": -2.5},
            "anchor": "target_center",
        },
        "hole": {
            "shape": "cylindrical",
            "diameter_mm": 2.0,
            "depth_mm": 12.5,
            "axis": "z",
            "drill_from": "positive_z_face",
        },
        "realization": {
            "mode": "boolean_subtraction",
            "status": "generated",
            "result_solid_ref": {"id": "solid-result-1", "name": "collimator_block_drilled"},
            "generated_object_refs": {
                "solid_refs": [
                    {"id": "solid-result-1", "name": "collimator_block_drilled"},
                    {"id": "solid-cutter-1", "name": "collimator_hole_cutter"},
                ],
                "logical_volume_refs": [
                    {"id": "lv-target-1", "name": "collimator_lv"},
                ],
                "placement_refs": [
                    {"id": "pv-target-1", "name": "collimator_pv"},
                ],
            },
        },
    }

    state = GeometryState.from_dict({"detector_feature_generators": [valid_payload]})
    assert state.detector_feature_generators == [expected_payload]
    assert state.to_dict()["detector_feature_generators"] == [expected_payload]

    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.detector_feature_generators = [expected_payload]

    json_string = pm.save_project_to_json_string()
    saved_payload = json.loads(json_string)
    assert saved_payload["detector_feature_generators"] == [expected_payload]

    pm_round_tripped = ProjectManager(ExpressionEvaluator())
    pm_round_tripped.load_project_from_json_string(json_string)
    assert pm_round_tripped.current_geometry_state.detector_feature_generators == [expected_payload]


def test_rectangular_drilled_hole_generator_realization_creates_boolean_geometry_and_updates_targets():
    pm = _make_pm()

    solid_dict, error_msg = pm.add_solid(
        "collimator_block",
        "box",
        {"x": "20", "y": "12", "z": "10"},
    )
    assert error_msg is None
    assert solid_dict["name"] == "collimator_block"

    lv_a, error_msg = pm.add_logical_volume("collimator_lv", "collimator_block", "G4_Galactic")
    assert error_msg is None
    lv_b, error_msg = pm.add_logical_volume("collimator_lv_copy", "collimator_block", "G4_Galactic")
    assert error_msg is None

    pv_a, error_msg = pm.add_physical_volume(
        "World",
        "collimator_pv",
        "collimator_lv",
        {"x": "0", "y": "0", "z": "0"},
        {"x": "0", "y": "0", "z": "0"},
        {"x": "1", "y": "1", "z": "1"},
    )
    assert error_msg is None
    pv_b, error_msg = pm.add_physical_volume(
        "World",
        "collimator_pv_copy",
        "collimator_lv_copy",
        {"x": "40", "y": "0", "z": "0"},
        {"x": "0", "y": "0", "z": "0"},
        {"x": "1", "y": "1", "z": "1"},
    )
    assert error_msg is None

    pm.current_geometry_state.detector_feature_generators = _normalize_detector_feature_generators([
        {
            "generator_id": "dfg_rect_holes_runtime",
            "name": "fixture_collimator_holes",
            "generator_type": "rectangular_drilled_hole_array",
            "target": {
                "solid_ref": {
                    "id": solid_dict["id"],
                    "name": solid_dict["name"],
                },
            },
            "pattern": {
                "count_x": 2,
                "count_y": 2,
                "pitch_mm": {"x": 4, "y": 5},
                "origin_offset_mm": {"x": 1, "y": -1},
            },
            "hole": {
                "diameter_mm": 2,
                "depth_mm": 6,
            },
        }
    ])

    result, error_msg = pm.realize_detector_feature_generator("dfg_rect_holes_runtime")
    assert error_msg is None
    assert result["hole_count"] == 4
    assert result["updated_logical_volume_names"] == ["collimator_lv", "collimator_lv_copy"]

    cutter_name = result["cutter_solid_name"]
    result_name = result["result_solid_name"]
    cutter_solid = pm.current_geometry_state.solids[cutter_name]
    result_solid = pm.current_geometry_state.solids[result_name]

    assert cutter_solid.type == "tube"
    assert float(cutter_solid.raw_parameters["rmax"]) == pytest.approx(1.0)
    assert float(cutter_solid.raw_parameters["z"]) == pytest.approx(6.0)

    assert result_solid.type == "boolean"
    recipe = result_solid.raw_parameters["recipe"]
    assert recipe[0] == {"op": "base", "solid_ref": "collimator_block"}
    assert len(recipe) == 5

    positions = [
        (
            float(item["transform"]["position"]["x"]),
            float(item["transform"]["position"]["y"]),
            float(item["transform"]["position"]["z"]),
        )
        for item in recipe[1:]
    ]
    assert positions == pytest.approx(
        [
            (-1.0, -3.5, 2.0),
            (3.0, -3.5, 2.0),
            (-1.0, 1.5, 2.0),
            (3.0, 1.5, 2.0),
        ]
    )

    assert pm.current_geometry_state.logical_volumes["collimator_lv"].solid_ref == result_name
    assert pm.current_geometry_state.logical_volumes["collimator_lv_copy"].solid_ref == result_name

    entry = pm.current_geometry_state.detector_feature_generators[0]
    assert entry["realization"]["status"] == "generated"
    assert entry["realization"]["result_solid_ref"] == {
        "id": result_solid.id,
        "name": result_name,
    }
    assert entry["realization"]["generated_object_refs"]["solid_refs"] == [
        {"id": result_solid.id, "name": result_name},
        {"id": cutter_solid.id, "name": cutter_name},
    ]
    assert entry["realization"]["generated_object_refs"]["logical_volume_refs"] == [
        {"id": lv_a["id"], "name": "collimator_lv"},
        {"id": lv_b["id"], "name": "collimator_lv_copy"},
    ]
    assert entry["realization"]["generated_object_refs"]["placement_refs"] == [
        {"id": pv_a["id"], "name": "collimator_pv"},
        {"id": pv_b["id"], "name": "collimator_pv_copy"},
    ]


def test_rectangular_drilled_hole_generator_realization_reuses_generated_solids_on_revision():
    pm = _make_pm()

    solid_dict, error_msg = pm.add_solid(
        "revision_block",
        "box",
        {"x": "30", "y": "20", "z": "10"},
    )
    assert error_msg is None

    _, error_msg = pm.add_logical_volume("revision_lv", "revision_block", "G4_Galactic")
    assert error_msg is None

    pm.current_geometry_state.detector_feature_generators = _normalize_detector_feature_generators([
        {
            "generator_id": "dfg_rect_holes_refresh",
            "name": "refresh_collimator_holes",
            "generator_type": "rectangular_drilled_hole_array",
            "target": {
                "solid_ref": {
                    "id": solid_dict["id"],
                    "name": solid_dict["name"],
                },
            },
            "pattern": {
                "count_x": 1,
                "count_y": 1,
                "pitch_mm": {"x": 4, "y": 4},
                "origin_offset_mm": {"x": 0, "y": 0},
            },
            "hole": {
                "diameter_mm": 1.5,
                "depth_mm": 4,
            },
        }
    ])

    first_result, error_msg = pm.realize_detector_feature_generator("dfg_rect_holes_refresh")
    assert error_msg is None

    first_result_name = first_result["result_solid_name"]
    first_cutter_name = first_result["cutter_solid_name"]
    first_entry = pm.current_geometry_state.detector_feature_generators[0]
    first_solid_refs = {
        item["name"]: item["id"]
        for item in first_entry["realization"]["generated_object_refs"]["solid_refs"]
    }

    entry = pm.current_geometry_state.detector_feature_generators[0]
    entry["pattern"]["count_x"] = 3
    entry["pattern"]["pitch_mm"]["x"] = 5.0
    entry["hole"]["depth_mm"] = 10.0

    second_result, error_msg = pm.realize_detector_feature_generator("dfg_rect_holes_refresh")
    assert error_msg is None
    assert second_result["result_solid_name"] == first_result_name
    assert second_result["cutter_solid_name"] == first_cutter_name
    assert pm.current_geometry_state.logical_volumes["revision_lv"].solid_ref == first_result_name

    second_entry = pm.current_geometry_state.detector_feature_generators[0]
    second_solid_refs = {
        item["name"]: item["id"]
        for item in second_entry["realization"]["generated_object_refs"]["solid_refs"]
    }
    assert second_solid_refs == first_solid_refs

    refreshed_result_solid = pm.current_geometry_state.solids[first_result_name]
    refreshed_recipe = refreshed_result_solid.raw_parameters["recipe"]
    assert len(refreshed_recipe) == 4
    assert [
        (
            float(item["transform"]["position"]["x"]),
            float(item["transform"]["position"]["y"]),
            float(item["transform"]["position"]["z"]),
        )
        for item in refreshed_recipe[1:]
    ] == pytest.approx(
        [
            (-5.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (5.0, 0.0, 0.0),
        ]
    )

    generated_prefix_names = sorted(
        name
        for name in pm.current_geometry_state.solids
        if name.startswith("refresh_collimator_holes__")
    )
    assert generated_prefix_names == [first_cutter_name, first_result_name]


def test_circular_drilled_hole_generator_realization_creates_bolt_circle_geometry():
    pm = _make_pm()

    solid_dict, error_msg = pm.add_solid(
        "circular_block",
        "box",
        {"x": "24", "y": "24", "z": "10"},
    )
    assert error_msg is None

    logical_volume, error_msg = pm.add_logical_volume("circular_lv", "circular_block", "G4_Galactic")
    assert error_msg is None

    placement, error_msg = pm.add_physical_volume(
        "World",
        "circular_pv",
        "circular_lv",
        {"x": "0", "y": "0", "z": "0"},
        {"x": "0", "y": "0", "z": "0"},
        {"x": "1", "y": "1", "z": "1"},
    )
    assert error_msg is None

    pm.current_geometry_state.detector_feature_generators = _normalize_detector_feature_generators([
        {
            "generator_id": "dfg_circular_holes_runtime",
            "name": "fixture_circular_holes",
            "generator_type": "circular_drilled_hole_array",
            "target": {
                "solid_ref": {
                    "id": solid_dict["id"],
                    "name": solid_dict["name"],
                },
            },
            "pattern": {
                "count": 4,
                "radius_mm": 4,
                "orientation_deg": 45,
                "origin_offset_mm": {"x": 1, "y": -2},
            },
            "hole": {
                "diameter_mm": 2,
                "depth_mm": 6,
            },
        }
    ])

    result, error_msg = pm.realize_detector_feature_generator("dfg_circular_holes_runtime")
    assert error_msg is None
    assert result["hole_count"] == 4
    assert result["updated_logical_volume_names"] == ["circular_lv"]

    result_solid = pm.current_geometry_state.solids[result["result_solid_name"]]
    recipe = result_solid.raw_parameters["recipe"]
    assert recipe[0] == {"op": "base", "solid_ref": "circular_block"}
    assert len(recipe) == 5
    positions = [
        (
            float(item["transform"]["position"]["x"]),
            float(item["transform"]["position"]["y"]),
            float(item["transform"]["position"]["z"]),
        )
        for item in recipe[1:]
    ]
    expected_positions = [
        (3.82842712474619, 0.8284271247461903, 2.0),
        (-1.8284271247461898, 0.8284271247461903, 2.0),
        (-1.8284271247461907, -4.82842712474619, 2.0),
        (3.8284271247461894, -4.82842712474619, 2.0),
    ]
    for position, expected_position in zip(positions, expected_positions):
        assert position == pytest.approx(expected_position)

    entry = pm.current_geometry_state.detector_feature_generators[0]
    assert entry["realization"]["status"] == "generated"
    assert entry["realization"]["generated_object_refs"]["logical_volume_refs"] == [
        {"id": logical_volume["id"], "name": "circular_lv"},
    ]
    assert entry["realization"]["generated_object_refs"]["placement_refs"] == [
        {"id": placement["id"], "name": "circular_pv"},
    ]
    assert pm.current_geometry_state.logical_volumes["circular_lv"].solid_ref == result["result_solid_name"]


def test_upsert_detector_feature_generator_saves_and_regenerates_in_place():
    pm = _make_pm()

    solid_dict, error_msg = pm.add_solid(
        "ui_collimator_block",
        "box",
        {"x": "24", "y": "18", "z": "12"},
    )
    assert error_msg is None

    _, error_msg = pm.add_logical_volume("ui_collimator_lv", "ui_collimator_block", "G4_Galactic")
    assert error_msg is None

    created_entry, first_result, error_msg = pm.upsert_detector_feature_generator(
        {
            "generator_id": "dfg_ui_modal_fixture",
            "generator_type": "rectangular_drilled_hole_array",
            "name": "ui_collimator_holes",
            "target": {
                "solid_ref": {
                    "id": solid_dict["id"],
                    "name": solid_dict["name"],
                },
            },
            "pattern": {
                "count_x": 2,
                "count_y": 3,
                "pitch_mm": {"x": 4.5, "y": 6.0},
                "origin_offset_mm": {"x": 0.5, "y": -1.0},
            },
            "hole": {
                "diameter_mm": 1.5,
                "depth_mm": 8.0,
            },
        },
        realize_now=True,
    )

    assert error_msg is None
    assert first_result["hole_count"] == 6
    assert created_entry["realization"]["status"] == "generated"
    first_result_name = first_result["result_solid_name"]
    first_cutter_name = first_result["cutter_solid_name"]

    updated_entry, second_result, error_msg = pm.upsert_detector_feature_generator(
        {
            "generator_id": "dfg_ui_modal_fixture",
            "generator_type": "rectangular_drilled_hole_array",
            "name": "ui_collimator_holes",
            "target": {
                "solid_ref": {
                    "id": solid_dict["id"],
                    "name": solid_dict["name"],
                },
            },
            "pattern": {
                "count_x": 4,
                "count_y": 1,
                "pitch_mm": {"x": 3.0, "y": 6.0},
                "origin_offset_mm": {"x": -1.5, "y": 0.0},
            },
            "hole": {
                "diameter_mm": 2.0,
                "depth_mm": 10.0,
            },
        },
        realize_now=True,
    )

    assert error_msg is None
    assert second_result["hole_count"] == 4
    assert second_result["result_solid_name"] == first_result_name
    assert second_result["cutter_solid_name"] == first_cutter_name
    assert updated_entry["realization"]["result_solid_ref"]["name"] == first_result_name
    assert pm.current_geometry_state.logical_volumes["ui_collimator_lv"].solid_ref == first_result_name

    refreshed_recipe = pm.current_geometry_state.solids[first_result_name].raw_parameters["recipe"]
    assert len(refreshed_recipe) == 5
    assert [
        (
            float(item["transform"]["position"]["x"]),
            float(item["transform"]["position"]["y"]),
            float(item["transform"]["position"]["z"]),
        )
        for item in refreshed_recipe[1:]
    ] == pytest.approx(
        [
            (-6.0, 0.0, 1.0),
            (-3.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (3.0, 0.0, 1.0),
        ]
    )
