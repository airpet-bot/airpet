import json
from pathlib import Path

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_optical_boundary_invoke_sd_round_trip():
    state = GeometryState()
    assert state.environment.optical_boundary_invoke_sd is False

    state.environment.optical_boundary_invoke_sd = True
    payload = state.to_dict()
    assert payload["environment"]["optical_boundary_invoke_sd"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.optical_boundary_invoke_sd is True


def test_environment_state_validation_rejects_non_bool():
    ok, err = EnvironmentState.validate({"optical_boundary_invoke_sd": "yes"})
    assert ok is False
    assert "optical_boundary_invoke_sd must be a boolean" in err


def test_project_json_save_load_persists_optical_boundary_invoke_sd():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.optical_boundary_invoke_sd = True

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["optical_boundary_invoke_sd"] is True

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.optical_boundary_invoke_sd is True


def test_generate_macro_emits_optical_boundary_invoke_sd_when_true(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.optical_boundary_invoke_sd = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "optical-sd-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/boundary/setInvokeSD true" in macro_text


def test_generate_macro_emits_optical_boundary_invoke_sd_when_false(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.optical_boundary_invoke_sd = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "optical-sd-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/boundary/setInvokeSD false" in macro_text


def test_generate_macro_omits_optical_boundary_invoke_sd_when_optical_physics_off(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = False
    state.environment.optical_boundary_invoke_sd = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "optical-sd-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/optical/boundary/setInvokeSD" not in macro_text
