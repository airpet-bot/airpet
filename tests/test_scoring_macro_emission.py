import json
from pathlib import Path

import pytest

from src.geometry_types import GeometryState, ScoringState
from src.project_manager import ProjectManager
from src.expression_evaluator import ExpressionEvaluator


def test_generate_macro_emits_score_commands_for_enabled_meshes(tmp_path):
    """Verify that generate_macro_file emits /score/ commands for enabled
    scoring meshes and omits disabled ones."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_enabled",
                "name": "enabled_mesh",
                "enabled": True,
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "size_mm": {"x": 40, "y": 20, "z": 10},
                },
                "bins": {"x": 8, "y": 4, "z": 2},
            },
            {
                "mesh_id": "mesh_disabled",
                "name": "disabled_mesh",
                "enabled": False,
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 10.0, "y": 20.0, "z": 30.0},
                    "size_mm": {"x": 100, "y": 100, "z": 100},
                },
                "bins": {"x": 10, "y": 10, "z": 10},
            },
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "score-mesh-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    # Enabled mesh commands
    assert "/score/create/boxMesh enabled_mesh" in macro_text
    assert "/score/mesh/boxSize 20 10 5 mm" in macro_text
    assert "/score/mesh/translate/xyz 1 2 3 mm" in macro_text
    assert "/score/mesh/nBin 8 4 2" in macro_text
    assert "/score/quantity/energyDeposit enabled_mesh_eDep" in macro_text
    assert "/score/close" in macro_text

    # Disabled mesh must not appear
    assert "/score/create/boxMesh disabled_mesh" not in macro_text
    assert "/score/mesh/translate/xyz 10 20 30 mm" not in macro_text

    # No duplicate close issues
    assert macro_text.count("/score/close") >= 1


def test_generate_macro_emits_particle_filter_for_tally_request(tmp_path):
    """Verify that a tally request with particle_filter emits /score/filter/particle."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_main",
                "name": "main_mesh",
                "enabled": True,
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 0, "y": 0, "z": 0},
                    "size_mm": {"x": 20, "y": 20, "z": 20},
                },
                "bins": {"x": 5, "y": 5, "z": 5},
            }
        ],
        "tally_requests": [
            {
                "tally_id": "tally_gamma",
                "name": "gamma_nOfStep",
                "mesh_ref": {"mesh_id": "mesh_main"},
                "quantity": "n_of_step",
                "particle_filter": {
                    "filter_name": "gammaFilter",
                    "particle": "gamma",
                },
            },
            {
                "tally_id": "tally_no_filter",
                "name": "energy_deposit",
                "mesh_ref": {"mesh_id": "mesh_main"},
                "quantity": "energy_deposit",
            },
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "filter-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/score/quantity/nOfStep gamma_nOfStep" in macro_text
    assert "/score/filter/particle gammaFilter gamma" in macro_text
    assert "/score/quantity/energyDeposit energy_deposit" in macro_text
    assert "energy_deposit_filter" not in macro_text


def test_generate_macro_emits_particle_filter_for_tally_requests(tmp_path):
    """Verify that tally requests with particle_filter emit /score/filter/particle."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_main",
                "name": "mesh_main",
                "geometry": {"size_mm": {"x": 20, "y": 20, "z": 20}},
                "bins": {"x": 10, "y": 10, "z": 10},
            }
        ],
        "tally_requests": [
            {
                "tally_id": "tally_gamma",
                "name": "gamma_nOfStep",
                "mesh_ref": {"mesh_id": "mesh_main"},
                "quantity": "n_of_step",
                "particle_filter": {
                    "filter_name": "gammaFilter",
                    "particle": "gamma",
                },
            },
            {
                "tally_id": "tally_neutron",
                "name": "neutron_track_length",
                "mesh_ref": {"mesh_id": "mesh_main"},
                "quantity": "track_length",
                "particle_filter": {
                    "filter_name": "neutronFilter",
                    "particle": "neutron",
                },
            },
            {
                "tally_id": "tally_unfiltered",
                "name": "unfiltered_energy",
                "mesh_ref": {"mesh_id": "mesh_main"},
                "quantity": "energy_deposit",
            },
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "filter-job", {}, str(tmp_path), str(tmp_path), str(version_dir)
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    # Filtered tallies should emit quantity then filter
    assert "/score/quantity/nOfStep gamma_nOfStep" in macro_text
    assert "/score/filter/particle gammaFilter gamma" in macro_text

    assert "/score/quantity/trackLength neutron_track_length" in macro_text
    assert "/score/filter/particle neutronFilter neutron" in macro_text

    # Unfiltered tally should not emit a filter line
    assert "/score/quantity/energyDeposit unfiltered_energy" in macro_text
    assert "unfiltered_energy_filter" not in macro_text


def test_generate_macro_emits_cylinder_mesh_commands(tmp_path):
    """Verify that generate_macro_file emits /score/create/cylinderMesh and
    related commands for cylindrical scoring meshes."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_cyl",
                "name": "cyl_mesh",
                "enabled": True,
                "mesh_type": "cylinder",
                "geometry": {
                    "center_mm": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "size_mm": {"rmin": 5.0, "rmax": 15.0, "z": 20.0},
                },
                "bins": {"r": 4, "phi": 8, "z": 2},
            },
            {
                "mesh_id": "mesh_box",
                "name": "box_mesh",
                "enabled": True,
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 0, "y": 0, "z": 0},
                    "size_mm": {"x": 10, "y": 10, "z": 10},
                },
                "bins": {"x": 5, "y": 5, "z": 5},
            },
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "cylinder-mesh-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    # Cylinder mesh commands
    assert "/score/create/cylinderMesh cyl_mesh" in macro_text
    assert "/score/mesh/cylinderSize 5 15 20 mm" in macro_text
    assert "/score/mesh/translate/xyz 1 2 3 mm" in macro_text
    assert "/score/mesh/nBin 4 8 2" in macro_text

    # Box mesh commands still work
    assert "/score/create/boxMesh box_mesh" in macro_text
    assert "/score/mesh/boxSize 5 5 5 mm" in macro_text
    assert "/score/mesh/nBin 5 5 5" in macro_text

    # Both close properly
    assert macro_text.count("/score/close") == 2


def test_generate_macro_skips_scoring_section_when_no_meshes(tmp_path):
    """Verify that the macro comments out scoring when no meshes exist."""
    pm = ProjectManager(ExpressionEvaluator())

    state = GeometryState()
    state.scoring = ScoringState.from_dict({"scoring_meshes": []})

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "no-score-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "# --- Scoring Meshes ---" in macro_text
    assert "# No scoring meshes defined." in macro_text
    assert "/score/create/boxMesh" not in macro_text


def test_generate_macro_maps_new_quantities_to_g4_commands(tmp_path):
    """Verify that newly added tally quantities map to correct /score/quantity/ commands."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_new_qty",
                "name": "new_qty_mesh",
                "geometry": {"size_mm": {"x": 20, "y": 20, "z": 20}},
                "bins": {"x": 10, "y": 10, "z": 10},
            }
        ],
        "tally_requests": [
            {
                "tally_id": "t_nOfSecondary",
                "name": "nOfSecondary_tally",
                "mesh_ref": {"mesh_id": "mesh_new_qty"},
                "quantity": "n_of_secondary",
            },
            {
                "tally_id": "t_passageTrackLength",
                "name": "passageTrackLength_tally",
                "mesh_ref": {"mesh_id": "mesh_new_qty"},
                "quantity": "passage_track_length",
            },
            {
                "tally_id": "t_flatSurfaceCurrent",
                "name": "flatSurfaceCurrent_tally",
                "mesh_ref": {"mesh_id": "mesh_new_qty"},
                "quantity": "flat_surface_current",
            },
            {
                "tally_id": "t_flatSurfaceFlux",
                "name": "flatSurfaceFlux_tally",
                "mesh_ref": {"mesh_id": "mesh_new_qty"},
                "quantity": "flat_surface_flux",
            },
            {
                "tally_id": "t_nOfCollision",
                "name": "nOfCollision_tally",
                "mesh_ref": {"mesh_id": "mesh_new_qty"},
                "quantity": "n_of_collision",
            },
            {
                "tally_id": "t_population",
                "name": "population_tally",
                "mesh_ref": {"mesh_id": "mesh_new_qty"},
                "quantity": "population",
            },
        ],
    }

    state = GeometryState()
    state.scoring = ScoringState.from_dict(scoring_payload)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "new-qty-job", {}, str(tmp_path), str(tmp_path), str(version_dir)
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/score/quantity/nOfSecondary nOfSecondary_tally" in macro_text
    assert "/score/quantity/passageTrackLength passageTrackLength_tally" in macro_text
    assert "/score/quantity/flatSurfaceCurrent flatSurfaceCurrent_tally" in macro_text
    assert "/score/quantity/flatSurfaceFlux flatSurfaceFlux_tally" in macro_text
    assert "/score/quantity/nOfCollision nOfCollision_tally" in macro_text
    assert "/score/quantity/population population_tally" in macro_text


def test_generate_macro_emits_real_world_log_vol_commands(tmp_path):
    """Verify that generate_macro_file emits /score/create/realWorldLogVol and
    omits mesh geometry commands for realWorldLogVol meshes."""
    pm = ProjectManager(ExpressionEvaluator())

    scoring_payload = {
        "scoring_meshes": [
            {
                "mesh_id": "mesh_rwlv",
                "name": "rwlv_mesh",
                "enabled": True,
                "mesh_type": "realWorldLogVol",
                "geometry": {
                    "logical_volume_name": "box_LV",
                    "copy_number_level": 1,
                },
            },
            {
                "mesh_id": "mesh_box",
                "name": "box_mesh",
                "enabled": True,
                "mesh_type": "box",
                "geometry": {
                    "center_mm": {"x": 0, "y": 0, "z": 0},
                    "size_mm": {"x": 10, "y": 10, "z": 10},
                },
                "bins": {"x": 5, "y": 5, "z": 5},
            },
        ],
        "tally_requests": [
            {
                "tally_id": "tally_rwlv",
                "name": "rwlv_energy",
                "mesh_ref": {"mesh_id": "mesh_rwlv"},
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
        pm.generate_macro_file(
            "rwlv-job", {}, str(tmp_path), str(tmp_path), str(version_dir)
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    # realWorldLogVol mesh commands
    assert "/score/create/realWorldLogVol box_LV 1" in macro_text
    assert "/score/quantity/energyDeposit rwlv_energy" in macro_text

    # Box mesh still works alongside realWorldLogVol
    assert "/score/create/boxMesh box_mesh" in macro_text

    # Both meshes close properly
    assert macro_text.count("/score/close") == 2
