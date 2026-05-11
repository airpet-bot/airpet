import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_em_process_round_trip():
    state = GeometryState()
    assert state.environment.em_apply_cuts is False
    assert state.environment.eloss_fluct is True

    state.environment.em_apply_cuts = True
    state.environment.eloss_fluct = False
    payload = state.to_dict()
    assert payload["environment"]["em_apply_cuts"] is True
    assert payload["environment"]["eloss_fluct"] is False

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.em_apply_cuts is True
    assert round_tripped.environment.eloss_fluct is False


def test_environment_state_validation_rejects_invalid_em_process_parameters():
    ok, err = EnvironmentState.validate({"em_apply_cuts": "yes"})
    assert ok is False
    assert "em_apply_cuts must be a boolean" in err

    ok, err = EnvironmentState.validate({"eloss_fluct": 1})
    assert ok is False
    assert "eloss_fluct must be a boolean" in err


def test_project_json_save_load_persists_em_process_parameters():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.em_apply_cuts = True
    pm.current_geometry_state.environment.eloss_fluct = False

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["em_apply_cuts"] is True
    assert data["environment"]["eloss_fluct"] is False

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.em_apply_cuts is True
    assert pm2.current_geometry_state.environment.eloss_fluct is False


def test_generate_macro_emits_em_apply_cuts_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.em_apply_cuts = True
    state.environment.eloss_fluct = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "em-job",
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
    assert em_index > init_index
    assert "/process/em/applyCuts true" in macro_text
    assert "/process/eLoss/fluct false" not in macro_text


def test_generate_macro_emits_eloss_fluct_when_false(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.em_apply_cuts = False
    state.environment.eloss_fluct = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "em-job",
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
    assert em_index > init_index
    assert "/process/eLoss/fluct false" in macro_text
    assert "/process/em/applyCuts true" not in macro_text


def test_generate_macro_emits_both_when_set(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.em_apply_cuts = True
    state.environment.eloss_fluct = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "em-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/em/applyCuts true" in macro_text
    assert "/process/eLoss/fluct false" in macro_text


def test_generate_macro_omits_em_process_parameters_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.em_apply_cuts = False
    state.environment.eloss_fluct = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "em-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "# --- EM Process Parameters ---" not in macro_text
    assert "/process/em/applyCuts" not in macro_text
    assert "/process/eLoss/fluct" not in macro_text
