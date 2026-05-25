import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_auger_cascade_pixe_deexcitation_round_trip():
    state = GeometryState()
    assert state.environment.auger_cascade is False
    assert state.environment.pixe is False
    assert state.environment.deexcitation_ignore_cut is False

    state.environment.auger_cascade = True
    state.environment.pixe = True
    state.environment.deexcitation_ignore_cut = True
    payload = state.to_dict()
    assert payload["environment"]["auger_cascade"] is True
    assert payload["environment"]["pixe"] is True
    assert payload["environment"]["deexcitation_ignore_cut"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.auger_cascade is True
    assert round_tripped.environment.pixe is True
    assert round_tripped.environment.deexcitation_ignore_cut is True


def test_environment_state_validation_rejects_invalid_auger_cascade_pixe_deexcitation():
    ok, err = EnvironmentState.validate({"auger_cascade": "yes"})
    assert ok is False
    assert "auger_cascade must be a boolean" in err

    ok, err = EnvironmentState.validate({"pixe": 1})
    assert ok is False
    assert "pixe must be a boolean" in err

    ok, err = EnvironmentState.validate({"deexcitation_ignore_cut": 1})
    assert ok is False
    assert "deexcitation_ignore_cut must be a boolean" in err


def test_project_json_save_load_persists_auger_cascade_pixe_deexcitation():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.auger_cascade = True
    pm.current_geometry_state.environment.pixe = True
    pm.current_geometry_state.environment.deexcitation_ignore_cut = True

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["auger_cascade"] is True
    assert data["environment"]["pixe"] is True
    assert data["environment"]["deexcitation_ignore_cut"] is True

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.auger_cascade is True
    assert pm2.current_geometry_state.environment.pixe is True
    assert pm2.current_geometry_state.environment.deexcitation_ignore_cut is True


def test_generate_macro_emits_auger_cascade_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.auger_cascade = True
    state.environment.pixe = False
    state.environment.deexcitation_ignore_cut = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "auger-cascade-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    init_index = macro_text.index("/run/initialize")
    em_index = macro_text.index("# --- EM Process Parameters ---")
    assert em_index < init_index
    assert "/process/em/augerCascade true" in macro_text
    assert "/process/em/pixe true" not in macro_text
    assert "/process/em/deexcitationIgnoreCut true" not in macro_text


def test_generate_macro_emits_pixe_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.auger_cascade = False
    state.environment.pixe = True
    state.environment.deexcitation_ignore_cut = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "pixe-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    init_index = macro_text.index("/run/initialize")
    em_index = macro_text.index("# --- EM Process Parameters ---")
    assert em_index < init_index
    assert "/process/em/pixe true" in macro_text
    assert "/process/em/augerCascade true" not in macro_text
    assert "/process/em/deexcitationIgnoreCut true" not in macro_text


def test_generate_macro_emits_deexcitation_ignore_cut_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.auger_cascade = False
    state.environment.pixe = False
    state.environment.deexcitation_ignore_cut = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "deexcitation-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    init_index = macro_text.index("/run/initialize")
    em_index = macro_text.index("# --- EM Process Parameters ---")
    assert em_index < init_index
    assert "/process/em/deexcitationIgnoreCut true" in macro_text
    assert "/process/em/augerCascade true" not in macro_text
    assert "/process/em/pixe true" not in macro_text


def test_generate_macro_emits_all_three_when_set(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.auger_cascade = True
    state.environment.pixe = True
    state.environment.deexcitation_ignore_cut = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "all-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/em/augerCascade true" in macro_text
    assert "/process/em/pixe true" in macro_text
    assert "/process/em/deexcitationIgnoreCut true" in macro_text


def test_generate_macro_omits_auger_cascade_pixe_deexcitation_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.auger_cascade = False
    state.environment.pixe = False
    state.environment.deexcitation_ignore_cut = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "default-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/em/augerCascade" not in macro_text
    assert "/process/em/pixe" not in macro_text
    assert "/process/em/deexcitationIgnoreCut" not in macro_text
