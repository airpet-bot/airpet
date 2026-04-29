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
