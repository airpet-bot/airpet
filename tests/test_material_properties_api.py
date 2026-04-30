"""Tests for backend API support of material optical properties."""

import json
import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import GeometryState, Material
from src.project_manager import ProjectManager


def test_add_material_with_optical_properties_survives_project_json_round_trip():
    """Adding a material with optical properties must survive save/load JSON round-trip."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    mat_dict, error = pm.add_material(
        "OpticalWater",
        {
            "Z_expr": "8",
            "A_expr": "16.00",
            "density_expr": "1.0*g/cm3",
            "state": "liquid",
            "properties": {
                "RINDEX": "WATERRINDEX",
                "ABSLENGTH": "WATERABSLENGTH",
                "SCINTILLATIONYIELD": "WATERSCINT",
            },
        },
    )
    assert error is None, error
    assert mat_dict is not None
    assert mat_dict["properties"] == {
        "RINDEX": "WATERRINDEX",
        "ABSLENGTH": "WATERABSLENGTH",
        "SCINTILLATIONYIELD": "WATERSCINT",
    }

    # Save project to JSON
    json_str = pm.save_project_to_json_string()
    project_data = json.loads(json_str)

    # Verify properties are in the JSON payload
    materials = project_data["materials"]
    assert "OpticalWater" in materials
    assert materials["OpticalWater"]["properties"] == {
        "RINDEX": "WATERRINDEX",
        "ABSLENGTH": "WATERABSLENGTH",
        "SCINTILLATIONYIELD": "WATERSCINT",
    }

    # Load project from JSON into a fresh manager
    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_str)

    loaded_mat = pm2.current_geometry_state.materials["OpticalWater"]
    assert loaded_mat.properties == {
        "RINDEX": "WATERRINDEX",
        "ABSLENGTH": "WATERABSLENGTH",
        "SCINTILLATIONYIELD": "WATERSCINT",
    }


def test_update_material_optical_properties():
    """Updating a material's optical properties via the API must persist."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    pm.add_material(
        "PlainWater",
        {
            "Z_expr": "8",
            "A_expr": "16.00",
            "density_expr": "1.0*g/cm3",
            "state": "liquid",
        },
    )

    # Initially no properties
    assert pm.current_geometry_state.materials["PlainWater"].properties == {}

    # Update with properties
    success, error = pm.update_material(
        "PlainWater",
        {"properties": {"RINDEX": "WATERRINDEX", "RAYLEIGH": "WATERRAYLEIGH"}},
    )
    assert error is None, error
    assert success is True

    assert pm.current_geometry_state.materials["PlainWater"].properties == {
        "RINDEX": "WATERRINDEX",
        "RAYLEIGH": "WATERRAYLEIGH",
    }

    # Round-trip through JSON
    json_str = pm.save_project_to_json_string()
    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_str)

    assert pm2.current_geometry_state.materials["PlainWater"].properties == {
        "RINDEX": "WATERRINDEX",
        "RAYLEIGH": "WATERRAYLEIGH",
    }


def test_material_properties_from_dict_restores_empty_dict():
    """Material.from_dict must restore properties as an empty dict when omitted."""
    data = {
        "id": "test-id",
        "name": "TestMat",
        "mat_type": "standard",
        "Z_expr": "14",
        "A_expr": "28.085",
        "density_expr": "2.33",
        "state": "solid",
        "components": [],
    }
    mat = Material.from_dict(data)
    assert mat.properties == {}


def test_material_properties_from_dict_restores_values():
    """Material.from_dict must restore properties when present."""
    data = {
        "id": "test-id",
        "name": "TestMat",
        "mat_type": "standard",
        "Z_expr": "14",
        "A_expr": "28.085",
        "density_expr": "2.33",
        "state": "solid",
        "components": [],
        "properties": {"RINDEX": "RINDEX_TABLE"},
    }
    mat = Material.from_dict(data)
    assert mat.properties == {"RINDEX": "RINDEX_TABLE"}
