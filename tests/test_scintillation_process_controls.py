import json
from pathlib import Path

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_scintillation_round_trip():
    state = GeometryState()
    assert state.environment.scintillation_by_particle_type is False
    assert state.environment.scintillation_finite_rise_time is False

    state.environment.scintillation_by_particle_type = True
    state.environment.scintillation_finite_rise_time = True
    payload = state.to_dict()
    assert payload["environment"]["scintillation_by_particle_type"] is True
    assert payload["environment"]["scintillation_finite_rise_time"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.scintillation_by_particle_type is True
    assert round_tripped.environment.scintillation_finite_rise_time is True


def test_environment_state_validation_rejects_non_bool():
    ok, err = EnvironmentState.validate({"scintillation_by_particle_type": "yes"})
    assert ok is False
    assert "scintillation_by_particle_type must be a boolean" in err

    ok, err = EnvironmentState.validate({"scintillation_finite_rise_time": 1})
    assert ok is False
    assert "scintillation_finite_rise_time must be a boolean" in err


def test_project_json_save_load_persists_scintillation_controls():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.scintillation_by_particle_type = True
    pm.current_geometry_state.environment.scintillation_finite_rise_time = False

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["scintillation_by_particle_type"] is True
    assert data["environment"]["scintillation_finite_rise_time"] is False

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.scintillation_by_particle_type is True
    assert pm2.current_geometry_state.environment.scintillation_finite_rise_time is False


def test_generate_macro_emits_scintillation_by_particle_type(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.scintillation_by_particle_type = True
    state.environment.scintillation_finite_rise_time = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "scint-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/scintillation/setByParticleType true" in macro_text
    assert "/process/optical/scintillation/setFiniteRiseTime" not in macro_text


def test_generate_macro_emits_scintillation_finite_rise_time(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.scintillation_by_particle_type = False
    state.environment.scintillation_finite_rise_time = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "scint-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/scintillation/setFiniteRiseTime true" in macro_text
    assert "/process/optical/scintillation/setByParticleType" not in macro_text


def test_generate_macro_emits_combined_scintillation_controls(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.scintillation_by_particle_type = True
    state.environment.scintillation_finite_rise_time = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "scint-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/optical/scintillation/setByParticleType true" in macro_text
    assert "/process/optical/scintillation/setFiniteRiseTime true" in macro_text


def test_generate_macro_omits_scintillation_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.scintillation_by_particle_type = False
    state.environment.scintillation_finite_rise_time = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "scint-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/scintillation/setByParticleType" not in macro_text
    assert "/process/optical/scintillation/setFiniteRiseTime" not in macro_text


def test_generate_macro_omits_scintillation_when_optical_physics_off(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = False
    state.environment.scintillation_by_particle_type = True
    state.environment.scintillation_finite_rise_time = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "scint-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/optical/scintillation/setByParticleType" not in macro_text
    assert "/process/optical/scintillation/setFiniteRiseTime" not in macro_text
