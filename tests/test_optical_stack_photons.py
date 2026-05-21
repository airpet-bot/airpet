import json
from pathlib import Path

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_optical_stack_photons_round_trip():
    state = GeometryState()
    assert state.environment.cerenkov_stack_photons is True
    assert state.environment.scintillation_stack_photons is True

    state.environment.cerenkov_stack_photons = False
    state.environment.scintillation_stack_photons = False
    payload = state.to_dict()
    assert payload["environment"]["cerenkov_stack_photons"] is False
    assert payload["environment"]["scintillation_stack_photons"] is False

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.cerenkov_stack_photons is False
    assert round_tripped.environment.scintillation_stack_photons is False


def test_environment_state_validation_rejects_non_bool():
    ok, err = EnvironmentState.validate({"cerenkov_stack_photons": "yes"})
    assert ok is False
    assert "cerenkov_stack_photons must be a boolean" in err

    ok, err = EnvironmentState.validate({"scintillation_stack_photons": 1})
    assert ok is False
    assert "scintillation_stack_photons must be a boolean" in err


def test_project_json_save_load_persists_optical_stack_photons():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.cerenkov_stack_photons = False
    pm.current_geometry_state.environment.scintillation_stack_photons = False

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["cerenkov_stack_photons"] is False
    assert data["environment"]["scintillation_stack_photons"] is False

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.cerenkov_stack_photons is False
    assert pm2.current_geometry_state.environment.scintillation_stack_photons is False


def test_generate_macro_emits_cerenkov_stack_photons_false(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_stack_photons = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "stack-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setStackPhotons false" in macro_text
    assert "/process/optical/scintillation/setStackPhotons" not in macro_text


def test_generate_macro_emits_scintillation_stack_photons_false(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.scintillation_stack_photons = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "stack-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/scintillation/setStackPhotons false" in macro_text
    assert "/process/optical/cerenkov/setStackPhotons" not in macro_text


def test_generate_macro_emits_both_stack_photons_false(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_stack_photons = False
    state.environment.scintillation_stack_photons = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "stack-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setStackPhotons false" in macro_text
    assert "/process/optical/scintillation/setStackPhotons false" in macro_text


def test_generate_macro_omits_stack_photons_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_stack_photons = True
    state.environment.scintillation_stack_photons = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "stack-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setStackPhotons" not in macro_text
    assert "/process/optical/scintillation/setStackPhotons" not in macro_text


def test_generate_macro_omits_stack_photons_when_optical_physics_off(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = False
    state.environment.cerenkov_stack_photons = False
    state.environment.scintillation_stack_photons = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "stack-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setStackPhotons" not in macro_text
    assert "/process/optical/scintillation/setStackPhotons" not in macro_text
