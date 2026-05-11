import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_process_inactivation_round_trip():
    state = GeometryState()
    assert state.environment.process_inactivation == []

    state.environment.process_inactivation = [
        {"process_name": "msc"},
        {"process_name": "eBrem", "particle": "e-"},
    ]
    payload = state.to_dict()
    assert payload["environment"]["process_inactivation"] == [
        {"process_name": "msc"},
        {"process_name": "eBrem", "particle": "e-"},
    ]

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.process_inactivation == [
        {"process_name": "msc"},
        {"process_name": "eBrem", "particle": "e-"},
    ]


def test_environment_state_validation_rejects_invalid_process_inactivation():
    ok, err = EnvironmentState.validate({"process_inactivation": "not-a-list"})
    assert ok is False
    assert "process_inactivation must be an array" in err

    ok, err = EnvironmentState.validate({"process_inactivation": [{}]})
    assert ok is False
    assert "process_inactivation[0].process_name must be a non-empty string" in err

    ok, err = EnvironmentState.validate({"process_inactivation": [{"process_name": ""}]})
    assert ok is False
    assert "process_inactivation[0].process_name must be a non-empty string" in err


def test_project_json_save_load_persists_process_inactivation():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.process_inactivation = [
        {"process_name": "msc", "particle": "e-"},
    ]

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["process_inactivation"] == [
        {"process_name": "msc", "particle": "e-"},
    ]

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.process_inactivation == [
        {"process_name": "msc", "particle": "e-"},
    ]


def test_generate_macro_emits_process_inactivation_after_initialize(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.process_inactivation = [
        {"process_name": "msc"},
        {"process_name": "eBrem", "particle": "e-"},
    ]

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "proc-inact-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    init_index = macro_text.index("/run/initialize")
    inact_index = macro_text.index("# --- Process Inactivation ---")
    assert inact_index > init_index
    assert "/process/inactivate msc" in macro_text
    assert "/process/inactivate eBrem e-" in macro_text


def test_generate_macro_omits_process_inactivation_when_empty(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.process_inactivation = []

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "proc-inact-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "# --- Process Inactivation ---" not in macro_text
    assert "/process/inactivate" not in macro_text
