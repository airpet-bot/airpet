import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_fluo_auger_round_trip():
    state = GeometryState()
    assert state.environment.fluo is False
    assert state.environment.auger is False

    state.environment.fluo = True
    state.environment.auger = True
    payload = state.to_dict()
    assert payload["environment"]["fluo"] is True
    assert payload["environment"]["auger"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.fluo is True
    assert round_tripped.environment.auger is True


def test_environment_state_validation_rejects_invalid_fluo_auger():
    ok, err = EnvironmentState.validate({"fluo": "yes"})
    assert ok is False
    assert "fluo must be a boolean" in err

    ok, err = EnvironmentState.validate({"auger": 1})
    assert ok is False
    assert "auger must be a boolean" in err


def test_project_json_save_load_persists_fluo_auger():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.fluo = True
    pm.current_geometry_state.environment.auger = True

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["fluo"] is True
    assert data["environment"]["auger"] is True

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.fluo is True
    assert pm2.current_geometry_state.environment.auger is True


def test_generate_macro_emits_fluo_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.fluo = True
    state.environment.auger = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "fluo-job",
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
    assert "/process/em/fluo true" in macro_text
    assert "/process/em/auger true" not in macro_text


def test_generate_macro_emits_auger_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.fluo = False
    state.environment.auger = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "auger-job",
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
    assert "/process/em/auger true" in macro_text
    assert "/process/em/fluo true" not in macro_text


def test_generate_macro_emits_both_when_set(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.fluo = True
    state.environment.auger = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "both-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/em/fluo true" in macro_text
    assert "/process/em/auger true" in macro_text


def test_generate_macro_omits_fluo_auger_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.fluo = False
    state.environment.auger = False

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

    assert "/process/em/fluo" not in macro_text
    assert "/process/em/auger" not in macro_text
