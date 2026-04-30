"""Tests for material optical properties runtime mapping in C++ and macro emission."""

import json
import os
import pytest
import tempfile

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import GeometryState, Material, Define, LogicalVolume, Solid
from src.gdml_writer import GDMLWriter
from src.project_manager import ProjectManager


def test_gdml_writer_skips_dangling_property_refs():
    """GDML writer must skip property tags when the referenced matrix is not defined."""
    state = GeometryState()
    state.add_solid(Solid("box_solid", "box", {"x": "10", "y": "10", "z": "10"}))
    mat = Material(
        "OpticalAir",
        Z_expr="14",
        A_expr="28.085",
        density_expr="0.001225*g/cm3",
        state="gas",
        properties={"RINDEX": "AIRRINDEX"},  # AIRRINDEX is not defined
    )
    state.add_material(mat)
    state.add_logical_volume(LogicalVolume("lv", "box_solid", "OpticalAir"))
    state.world_volume_ref = "lv"

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    # Should NOT contain the property tag because matrix is missing
    assert '<property name="RINDEX" ref="AIRRINDEX"/>' not in gdml_str
    # Should still contain the material
    assert '<material name="OpticalAir"' in gdml_str


def test_gdml_writer_emits_property_when_matrix_defined():
    """GDML writer must emit property tags when the referenced matrix exists in defines."""
    state = GeometryState()
    state.add_solid(Solid("box_solid", "box", {"x": "10", "y": "10", "z": "10"}))
    mat = Material(
        "OpticalWater",
        Z_expr="8",
        A_expr="16.00",
        density_expr="1.0*g/cm3",
        state="liquid",
        properties={"RINDEX": "WATERRINDEX"},
    )
    state.add_material(mat)
    # Define the matrix
    state.add_define(Define("WATERRINDEX", "matrix", {"coldim": "2", "values": ["1.0", "1.33", "2.0", "1.34"]}))
    state.add_logical_volume(LogicalVolume("lv", "box_solid", "OpticalWater"))
    state.world_volume_ref = "lv"

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    # Should contain both the matrix define and the property tag
    assert '<matrix name="WATERRINDEX"' in gdml_str
    assert '<property name="RINDEX" ref="WATERRINDEX"/>' in gdml_str


def test_generate_macro_emits_material_property_const_for_numeric_values():
    """Macro generation must emit addMaterialPropertyConst for numeric property values."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    pm.add_material(
        "Scintillator",
        {
            "Z_expr": "6",
            "A_expr": "12.01",
            "density_expr": "1.032*g/cm3",
            "state": "solid",
            "properties": {
                "SCINTILLATIONYIELD": "50.0",
                "RESOLUTIONSCALE": "1.0",
                "RINDEX": "RINDEX_TABLE",  # non-numeric, should be skipped
            },
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        version_dir = os.path.join(tmpdir, "version")
        run_dir = os.path.join(tmpdir, "run")
        os.makedirs(version_dir)
        os.makedirs(run_dir)

        # Save version.json so generate_macro_file can load it
        version_json = pm.save_project_to_json_string()
        with open(os.path.join(version_dir, "version.json"), "w") as f:
            f.write(version_json)

        macro_path = pm.generate_macro_file(
            job_id="test-job",
            sim_params={"events": 10},
            build_dir=tmpdir,
            run_dir=run_dir,
            version_dir=version_dir,
        )

        with open(macro_path, "r") as f:
            macro_content = f.read()

        assert "/g4pet/detector/addMaterialPropertyConst Scintillator|SCINTILLATIONYIELD|50.0" in macro_content
        assert "/g4pet/detector/addMaterialPropertyConst Scintillator|RESOLUTIONSCALE|1.0" in macro_content
        assert "RINDEX_TABLE" not in macro_content


def test_generate_macro_skips_material_properties_when_none_numeric():
    """Macro generation should not emit material property commands when no numeric values exist."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    pm.add_material(
        "OpticalAir",
        {
            "Z_expr": "14",
            "A_expr": "28.085",
            "density_expr": "0.001225*g/cm3",
            "state": "gas",
            "properties": {"RINDEX": "AIRRINDEX"},
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        version_dir = os.path.join(tmpdir, "version")
        run_dir = os.path.join(tmpdir, "run")
        os.makedirs(version_dir)
        os.makedirs(run_dir)

        version_json = pm.save_project_to_json_string()
        with open(os.path.join(version_dir, "version.json"), "w") as f:
            f.write(version_json)

        macro_path = pm.generate_macro_file(
            job_id="test-job",
            sim_params={"events": 10},
            build_dir=tmpdir,
            run_dir=run_dir,
            version_dir=version_dir,
        )

        with open(macro_path, "r") as f:
            macro_content = f.read()

        assert "# No material optical properties defined." in macro_content
        assert "/g4pet/detector/addMaterialPropertyConst" not in macro_content


def test_generate_macro_emits_material_property_vector():
    """Macro generation must emit addMaterialProperty for list property values."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    pm.add_material(
        "OpticalWater",
        {
            "Z_expr": "8",
            "A_expr": "16.00",
            "density_expr": "1.0*g/cm3",
            "state": "liquid",
            "properties": {
                # Values in keV (AIRPET internal energy unit); macro emits MeV for Geant4
                "RINDEX": [[1.0, 1.33], [2.0, 1.34], [3.0, 1.35]],
                "ABSLENGTH": "WATERABSLENGTH",  # non-numeric non-list, should be skipped
            },
        },
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        version_dir = os.path.join(tmpdir, "version")
        run_dir = os.path.join(tmpdir, "run")
        os.makedirs(version_dir)
        os.makedirs(run_dir)

        version_json = pm.save_project_to_json_string()
        with open(os.path.join(version_dir, "version.json"), "w") as f:
            f.write(version_json)

        macro_path = pm.generate_macro_file(
            job_id="test-job",
            sim_params={"events": 10},
            build_dir=tmpdir,
            run_dir=run_dir,
            version_dir=version_dir,
        )

        with open(macro_path, "r") as f:
            macro_content = f.read()

        # Energies converted from keV to MeV (multiply by 0.001)
        assert "/g4pet/detector/addMaterialProperty OpticalWater|RINDEX|3|0.001|1.33|0.002|1.34|0.003|1.35" in macro_content
        assert "WATERABSLENGTH" not in macro_content


def test_gdml_writer_emits_vector_properties_as_matrices():
    """GDML writer must create coldim=\"2\" matrix defines for list property values."""
    state = GeometryState()
    state.add_solid(Solid("box_solid", "box", {"x": "10", "y": "10", "z": "10"}))
    mat = Material(
        "OpticalWater",
        Z_expr="8",
        A_expr="16.00",
        density_expr="1.0*g/cm3",
        state="liquid",
        properties={"RINDEX": [[1.0, 1.33], [2.0, 1.34]]},
    )
    state.add_material(mat)
    state.add_logical_volume(LogicalVolume("lv", "box_solid", "OpticalWater"))
    state.world_volume_ref = "lv"

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    assert '<matrix name="OpticalWater_RINDEX_matprop_vec"' in gdml_str
    assert 'coldim="2"' in gdml_str
    assert '<property name="RINDEX" ref="OpticalWater_RINDEX_matprop_vec"/>' in gdml_str


def test_cpp_app_compiles_with_vector_property_support():
    """The C++ executable must exist after successful compilation."""
    build_dir = os.path.join(os.path.dirname(__file__), "..", "geant4", "build")
    executable = os.path.join(build_dir, "airpet-sim")
    assert os.path.exists(executable), f"C++ executable not found at {executable}"
