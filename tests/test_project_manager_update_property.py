import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import ParamVolume
from src.project_manager import ProjectManager


def _make_pm():
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()
    return pm


def _seed_parameterised_lv_content(pm):
    child_lv, err = pm.add_logical_volume("parameterised_child_lv", "box_solid", "G4_Galactic")
    assert err is None

    parent_lv = pm.current_geometry_state.logical_volumes["box_LV"]
    parent_lv.content_type = "parameterised"
    parent_lv.content = ParamVolume.from_dict(
        {
            "volume_ref": child_lv["name"],
            "ncopies": "1",
            "parameters": [
                {
                    "number": "0",
                    "position": {"x": "0", "y": "0", "z": "0"},
                    "rotation": {"x": "0", "y": "0", "z": "0"},
                    "dimensions_type": "box_dimensions",
                    "dimensions": {"x": "10", "y": "11", "z": "12"},
                }
            ],
        }
    )

    success, error = pm.recalculate_geometry_state()
    assert success is True
    assert error is None


@pytest.mark.parametrize("property_path", [".material_ref", "material_ref.", "content..number", "content...number"])
def test_update_object_property_rejects_invalid_nested_path_segments(property_path):
    pm = _make_pm()

    success, error = pm.update_object_property(
        "logical_volume",
        "box_LV",
        property_path,
        "G4_Si",
    )

    assert success is False
    assert error == f"Invalid property path '{property_path}'"


@pytest.mark.parametrize("property_path", [None, "", "   "])
def test_update_object_property_rejects_non_string_or_blank_property_path(property_path):
    pm = _make_pm()

    success, error = pm.update_object_property(
        "logical_volume",
        "box_LV",
        property_path,
        "G4_Si",
    )

    assert success is False
    assert error == f"Invalid property path '{property_path}'"


def test_update_object_property_reports_intermediate_dict_traversal_failures():
    pm = _make_pm()

    success, error = pm.update_object_property(
        "solid",
        "box_solid",
        "raw_parameters.inner.value",
        "10",
    )

    assert success is False
    assert error.startswith("Invalid property path 'raw_parameters.inner.value':")
    assert "'inner'" in error


def test_update_object_property_reports_intermediate_object_traversal_failures():
    pm = _make_pm()

    success, error = pm.update_object_property(
        "logical_volume",
        "World",
        "content.missing_attr.value",
        "10",
    )

    assert success is False
    assert error.startswith("Invalid property path 'content.missing_attr.value':")
    assert "missing_attr" in error


def test_update_object_property_keeps_valid_nested_dict_updates_working():
    pm = _make_pm()

    success, error = pm.update_object_property(
        "solid",
        "box_solid",
        "raw_parameters.x",
        "250",
    )

    assert success is True
    assert error is None
    assert pm.current_geometry_state.solids["box_solid"].raw_parameters["x"] == "250"


def test_update_object_property_supports_list_segment_traversal_for_nested_paths():
    pm = _make_pm()
    _seed_parameterised_lv_content(pm)

    success, error = pm.update_object_property(
        "logical_volume",
        "box_LV",
        "content.parameters.0.position.x",
        "42",
    )

    assert success is True
    assert error is None
    parameter = pm.current_geometry_state.logical_volumes["box_LV"].content.parameters[0]
    assert parameter.position["x"] == "42"


def test_update_object_property_rejects_non_numeric_list_segments():
    pm = _make_pm()
    _seed_parameterised_lv_content(pm)

    success, error = pm.update_object_property(
        "logical_volume",
        "box_LV",
        "content.parameters.first.position.x",
        "42",
    )

    assert success is False
    assert error.startswith("Invalid property path 'content.parameters.first.position.x':")
    assert "Expected list index segment" in error


def test_update_object_property_rejects_out_of_range_list_segments():
    pm = _make_pm()
    _seed_parameterised_lv_content(pm)

    success, error = pm.update_object_property(
        "logical_volume",
        "box_LV",
        "content.parameters.2.position.x",
        "42",
    )

    assert success is False
    assert error.startswith("Invalid property path 'content.parameters.2.position.x':")
    assert "List index out of range" in error
