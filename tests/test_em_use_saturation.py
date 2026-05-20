import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_em_use_saturation_round_trip():
    state = GeometryState()
    assert state.environment.em_use_saturation is False

    state.environment.em_use_saturation = True
    payload = state.to_dict()
    assert payload["environment"]["em_use_saturation"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.em_use_saturation is True


def test_environment_state_validation_rejects_invalid_em_use_saturation():
    ok, err = EnvironmentState.validate({"em_use_saturation": "yes"})
    assert ok is False
    assert "em_use_saturation must be a boolean" in err

    ok, err = EnvironmentState.validate({"em_use_saturation": 1})
    assert ok is False
    assert "em_use_saturation must be a boolean" in err


def test_project_json_save_load_persists_em_use_saturation():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.em_use_saturation = True

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["em_use_saturation"] is True

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.em_use_saturation is True


def test_generate_macro_emits_em_use_saturation_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.em_use_saturation = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "em-saturation-job",
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
    assert "/process/em/UseG4EmSaturation true" in macro_text


def test_generate_macro_omits_em_use_saturation_at_default(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    assert state.environment.em_use_saturation is False

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

    assert "/process/em/UseG4EmSaturation true" not in macro_text
