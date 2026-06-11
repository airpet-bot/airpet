import xml.etree.ElementTree as ET

import pytest

from app import normalize_primitive_solid_params
from src.ai_tools import PRIMITIVE_SOLID_PARAM_SPECS
from src.expression_evaluator import ExpressionEvaluator
from src.gdml_writer import GDMLWriter
from src.geometry_types import GeometryState, Solid
from src.project_manager import ProjectManager


FULL_LENGTH_FIELDS = {
    "box": ("x", "y", "z"),
    "tube": ("z",),
    "cone": ("z",),
    "trd": ("x1", "x2", "y1", "y2", "z"),
    "para": ("x", "y", "z"),
    "trap": ("z", "y1", "x1", "x2", "y2", "x3", "x4"),
    "hype": ("z",),
    "twistedbox": ("x", "y", "z"),
    "twistedtrd": ("x1", "x2", "y1", "y2", "z"),
    "twistedtrap": ("z", "y1", "x1", "x2", "y2", "x3", "x4"),
    "twistedtubs": ("zlen",),
}


def test_ai_schema_explicitly_labels_all_gdml_full_length_fields():
    for solid_type, field_names in FULL_LENGTH_FIELDS.items():
        properties = PRIMITIVE_SOLID_PARAM_SPECS[solid_type]["properties"]
        for field_name in field_names:
            description = properties[field_name]["description"].lower()
            assert "full" in description, f"{solid_type}.{field_name}: {description}"
            assert "half-length" not in description


@pytest.mark.parametrize(
    "solid_type,alias,value,expected_expression",
    [
        ("tube", "halfZ", "50", "2*(50)"),
        ("tube", "halfLength", "2 cm", "2*((2)*cm)"),
        ("cone", "dz", "25mm", "2*((25)*mm)"),
        ("cone", "halfZ", "30", "2*(30)"),
    ],
)
def test_half_length_aliases_convert_to_canonical_full_length(
    solid_type,
    alias,
    value,
    expected_expression,
):
    normalized = normalize_primitive_solid_params(
        solid_type,
        {alias: value},
    )
    assert normalized["z"] == expected_expression


def test_canonical_full_length_takes_precedence_over_half_length_alias():
    normalized = normalize_primitive_solid_params(
        "tube",
        {"z": "120", "halfZ": "50"},
    )
    assert normalized["z"] == "120"


def test_evaluated_primitive_dimensions_keep_canonical_gdml_meaning():
    manager = ProjectManager(ExpressionEvaluator())
    manager.create_empty_project()
    fixtures = {
        "trd_full": (
            "trd",
            {"x1": "20", "x2": "30", "y1": "40", "y2": "50", "z": "60"},
        ),
        "trap_full": (
            "trap",
            {
                "z": "60",
                "y1": "20",
                "x1": "10",
                "x2": "12",
                "y2": "24",
                "x3": "14",
                "x4": "16",
            },
        ),
        "twistedbox_full": (
            "twistedbox",
            {"x": "20", "y": "30", "z": "40", "PhiTwist": "10*deg"},
        ),
        "twistedtrd_full": (
            "twistedtrd",
            {
                "x1": "20",
                "x2": "30",
                "y1": "40",
                "y2": "50",
                "z": "60",
                "PhiTwist": "10*deg",
            },
        ),
        "twistedtrap_full": (
            "twistedtrap",
            {
                "PhiTwist": "10*deg",
                "z": "60",
                "Theta": "0",
                "Phi": "0",
                "y1": "20",
                "x1": "10",
                "x2": "12",
                "y2": "24",
                "x3": "14",
                "x4": "16",
                "Alph": "0",
            },
        ),
        "twistedtubs_full": (
            "twistedtubs",
            {
                "twistedangle": "10*deg",
                "endinnerrad": "5",
                "endouterrad": "10",
                "zlen": "60",
                "phi": "180*deg",
            },
        ),
    }

    for name, (solid_type, params) in fixtures.items():
        created, error = manager.add_solid(name, solid_type, params)
        assert error is None, error
        assert created is not None

    success, error = manager.recalculate_geometry_state()
    assert success, error
    state = manager.current_geometry_state
    assert state.solids["trd_full"]._evaluated_parameters["x1"] == 20
    assert state.solids["trd_full"]._evaluated_parameters["z"] == 60
    assert state.solids["trap_full"]._evaluated_parameters["x1"] == 10
    assert state.solids["trap_full"]._evaluated_parameters["z"] == 60
    assert state.solids["twistedbox_full"]._evaluated_parameters["x"] == 20
    assert state.solids["twistedbox_full"]._evaluated_parameters["z"] == 40
    assert state.solids["twistedtrd_full"]._evaluated_parameters["x1"] == 20
    assert state.solids["twistedtrd_full"]._evaluated_parameters["z"] == 60
    assert state.solids["twistedtrap_full"]._evaluated_parameters["x1"] == 10
    assert state.solids["twistedtrap_full"]._evaluated_parameters["z"] == 60
    assert state.solids["twistedtubs_full"]._evaluated_parameters["zlen"] == 60


@pytest.mark.parametrize(
    "solid_type,params,expected",
    [
        ("box", {"x": "20", "y": "30", "z": "40"}, {"x": "20", "y": "30", "z": "40"}),
        ("tube", {"rmin": "0", "rmax": "10", "z": "40"}, {"z": "40"}),
        (
            "cone",
            {"rmin1": "0", "rmax1": "10", "rmin2": "0", "rmax2": "20", "z": "40"},
            {"z": "40"},
        ),
        (
            "trd",
            {"x1": "20", "x2": "30", "y1": "40", "y2": "50", "z": "60"},
            {"x1": "20", "x2": "30", "y1": "40", "y2": "50", "z": "60"},
        ),
        (
            "para",
            {"x": "20", "y": "30", "z": "40", "alpha": "0", "theta": "0", "phi": "0"},
            {"x": "20", "y": "30", "z": "40"},
        ),
        (
            "trap",
            {
                "z": "60",
                "y1": "20",
                "x1": "10",
                "x2": "12",
                "y2": "24",
                "x3": "14",
                "x4": "16",
            },
            {"z": "60", "y1": "20", "x1": "10", "x2": "12", "y2": "24", "x3": "14", "x4": "16"},
        ),
        (
            "hype",
            {"rmin": "5", "rmax": "10", "inst": "0", "outst": "0", "z": "60"},
            {"z": "60"},
        ),
        (
            "twistedbox",
            {"x": "20", "y": "30", "z": "40", "PhiTwist": "10"},
            {"x": "20", "y": "30", "z": "40"},
        ),
        (
            "twistedtrd",
            {
                "x1": "20",
                "x2": "30",
                "y1": "40",
                "y2": "50",
                "z": "60",
                "PhiTwist": "10",
            },
            {"x1": "20", "x2": "30", "y1": "40", "y2": "50", "z": "60"},
        ),
        (
            "twistedtrap",
            {
                "PhiTwist": "10",
                "z": "60",
                "Theta": "0",
                "Phi": "0",
                "y1": "20",
                "x1": "10",
                "x2": "12",
                "y2": "24",
                "x3": "14",
                "x4": "16",
                "Alph": "0",
            },
            {"z": "60", "y1": "20", "x1": "10", "x2": "12", "y2": "24", "x3": "14", "x4": "16"},
        ),
        (
            "twistedtubs",
            {
                "twistedangle": "10",
                "endinnerrad": "5",
                "endouterrad": "10",
                "zlen": "60",
                "phi": "180",
            },
            {"zlen": "60"},
        ),
    ],
)
def test_gdml_writer_emits_canonical_full_lengths_without_rescaling(
    solid_type,
    params,
    expected,
):
    state = GeometryState()
    state.add_solid(Solid("dimension_fixture", solid_type, params))
    root = ET.fromstring(GDMLWriter(state).get_gdml_string())
    solid_element = root.find(f"./solids/{solid_type}")

    assert solid_element is not None
    assert solid_element.get("lunit") == "mm"
    for field_name, expected_value in expected.items():
        assert solid_element.get(field_name) == expected_value
