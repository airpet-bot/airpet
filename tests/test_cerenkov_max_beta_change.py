import json
from pathlib import Path

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_cerenkov_max_beta_change_round_trip():
    state = GeometryState()
    assert state.environment.cerenkov_max_beta_change == 0.0

    state.environment.cerenkov_max_beta_change = 0.05
    payload = state.to_dict()
    assert payload["environment"]["cerenkov_max_beta_change"] == 0.05

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.cerenkov_max_beta_change == 0.05


def test_environment_state_validation_rejects_non_number():
    ok, err = EnvironmentState.validate({"cerenkov_max_beta_change": "fast"})
    assert ok is False
    assert "cerenkov_max_beta_change must be a number" in err


def test_project_json_save_load_persists_cerenkov_max_beta_change():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.cerenkov_max_beta_change = 0.01

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["cerenkov_max_beta_change"] == 0.01

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.cerenkov_max_beta_change == 0.01


def test_generate_macro_emits_cerenkov_max_beta_change_when_positive(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_max_beta_change = 0.02

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "cerenkov-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setMaxBetaChange 0.02" in macro_text


def test_generate_macro_omits_cerenkov_max_beta_change_at_default(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_max_beta_change = 0.0

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "cerenkov-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setMaxBetaChange" not in macro_text


def test_generate_macro_omits_cerenkov_max_beta_change_when_optical_physics_off(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = False
    state.environment.cerenkov_max_beta_change = 0.03

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "cerenkov-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/optical/cerenkov/setMaxBetaChange" not in macro_text
