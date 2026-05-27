"""Tests for scoring mesh rotation support (G4CAP-050)."""

import json
from pathlib import Path

import pytest

from src.geometry_types import GeometryState, ScoringState
from src.project_manager import ProjectManager
from src.expression_evaluator import ExpressionEvaluator


def test_generate_macro_emits_rotation_for_box_mesh(tmp_path):
    """Verify that generate_macro_file emits rotate commands for a box mesh."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_rot",
                "name": "mesh_rot",
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 1, "y": 2, "z": 3},
                    "size_mm": {"x": 10, "y": 10, "z": 10},
                    "rotate_x_deg": 15.0,
                    "rotate_y_deg": 30.0,
                    "rotate_z_deg": 45.0,
                },
                "bins": {"x": 5, "y": 5, "z": 5},
            }
        ],
        "tally_requests": [
            {
                "tally_id": "t1",
                "name": "t1",
                "mesh_ref": {"mesh_id": "mesh_rot"},
                "quantity": "energy_deposit",
            }
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file("rot-job", {}, str(tmp_path), str(tmp_path), str(version_dir))
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/score/mesh/rotate/rotateX 15 deg" in macro_text
    assert "/score/mesh/rotate/rotateY 30 deg" in macro_text
    assert "/score/mesh/rotate/rotateZ 45 deg" in macro_text
    # Rotation should appear after translate
    translate_idx = macro_text.index("/score/mesh/translate/xyz")
    rot_x_idx = macro_text.index("/score/mesh/rotate/rotateX")
    assert translate_idx < rot_x_idx


def test_generate_macro_emits_rotation_for_cylinder_mesh(tmp_path):
    """Verify that generate_macro_file emits rotate commands for a cylinder mesh."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "cyl_rot",
                "name": "cyl_rot",
                "mesh_type": "cylinder",
                "geometry": {
                    "center_mm": {"x": 0, "y": 0, "z": 0},
                    "size_mm": {"rmin": 0, "rmax": 10, "z": 20},
                    "rotate_x_deg": 10.5,
                    "rotate_y_deg": -5.0,
                    "rotate_z_deg": 0.0,
                },
                "bins": {"r": 4, "phi": 8, "z": 2},
            }
        ],
        "tally_requests": [
            {
                "tally_id": "t1",
                "name": "t1",
                "mesh_ref": {"mesh_id": "cyl_rot"},
                "quantity": "energy_deposit",
            }
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file("cyl-rot-job", {}, str(tmp_path), str(tmp_path), str(version_dir))
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/score/mesh/rotate/rotateX 10.5 deg" in macro_text
    assert "/score/mesh/rotate/rotateY -5 deg" in macro_text
    assert "/score/mesh/rotate/rotateZ" not in macro_text  # zero -> omitted


def test_generate_macro_omits_rotation_at_defaults(tmp_path):
    """Verify that zero rotation values are omitted from the macro."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_default",
                "name": "mesh_default",
                "geometry": {
                    "center_mm": {"x": 0, "y": 0, "z": 0},
                    "size_mm": {"x": 10, "y": 10, "z": 10},
                },
                "bins": {"x": 5, "y": 5, "z": 5},
            }
        ],
        "tally_requests": [
            {
                "tally_id": "t1",
                "name": "t1",
                "mesh_ref": {"mesh_id": "mesh_default"},
                "quantity": "energy_deposit",
            }
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file("no-rot-job", {}, str(tmp_path), str(tmp_path), str(version_dir))
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/score/mesh/rotate/rotateX" not in macro_text
    assert "/score/mesh/rotate/rotateY" not in macro_text
    assert "/score/mesh/rotate/rotateZ" not in macro_text


def test_rotation_round_trip_in_project_json():
    """Verify that rotation values survive project save/load round-trip."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_rt",
                "name": "mesh_rt",
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 1, "y": 2, "z": 3},
                    "size_mm": {"x": 20, "y": 20, "z": 20},
                    "rotate_x_deg": 12.5,
                    "rotate_y_deg": 25.0,
                    "rotate_z_deg": 37.5,
                },
                "bins": {"x": 4, "y": 4, "z": 4},
            }
        ],
    }

    success, error = pm.update_object_property("scoring", "scoring_state", "state", scoring_payload)
    assert success is True
    assert error is None

    mesh = pm.current_geometry_state.scoring.to_dict()["scoring_meshes"][0]
    assert mesh["geometry"]["rotate_x_deg"] == 12.5
    assert mesh["geometry"]["rotate_y_deg"] == 25.0
    assert mesh["geometry"]["rotate_z_deg"] == 37.5


def test_rotation_validation_rejects_non_numeric():
    """Verify that non-numeric rotation values fail validation."""
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_bad",
                "name": "mesh_bad",
                "geometry": {
                    "center_mm": {"x": 0, "y": 0, "z": 0},
                    "size_mm": {"x": 10, "y": 10, "z": 10},
                    "rotate_x_deg": "invalid",
                },
                "bins": {"x": 2, "y": 2, "z": 2},
            }
        ],
    }

    success, error = pm.update_object_property("scoring", "scoring_state", "state", scoring_payload)
    assert success is False
    assert "rotate_x_deg must be numeric" in error
