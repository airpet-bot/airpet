import json
from pathlib import Path

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_track_secondaries_first_round_trip():
    state = GeometryState()
    assert state.environment.cerenkov_track_secondaries_first is False
    assert state.environment.scintillation_track_secondaries_first is False

    state.environment.cerenkov_track_secondaries_first = True
    state.environment.scintillation_track_secondaries_first = True
    payload = state.to_dict()
    assert payload["environment"]["cerenkov_track_secondaries_first"] is True
    assert payload["environment"]["scintillation_track_secondaries_first"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.cerenkov_track_secondaries_first is True
    assert round_tripped.environment.scintillation_track_secondaries_first is True


def test_environment_state_validation_rejects_non_bool():
    ok, err = EnvironmentState.validate({"cerenkov_track_secondaries_first": "yes"})
    assert ok is False
    assert "cerenkov_track_secondaries_first must be a boolean" in err

    ok, err = EnvironmentState.validate({"scintillation_track_secondaries_first": 1})
    assert ok is False
    assert "scintillation_track_secondaries_first must be a boolean" in err


def test_project_json_save_load_persists_track_secondaries_first():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.cerenkov_track_secondaries_first = True
    pm.current_geometry_state.environment.scintillation_track_secondaries_first = False

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["cerenkov_track_secondaries_first"] is True
    assert data["environment"]["scintillation_track_secondaries_first"] is False

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.cerenkov_track_secondaries_first is True
    assert pm2.current_geometry_state.environment.scintillation_track_secondaries_first is False


def test_generate_macro_emits_cerenkov_track_secondaries_first(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_track_secondaries_first = True
    state.environment.scintillation_track_secondaries_first = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "track-first-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setTrackSecondariesFirst true" in macro_text
    assert "/process/optical/scintillation/setTrackSecondariesFirst" not in macro_text


def test_generate_macro_emits_scintillation_track_secondaries_first(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_track_secondaries_first = False
    state.environment.scintillation_track_secondaries_first = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "track-first-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/scintillation/setTrackSecondariesFirst true" in macro_text
    assert "/process/optical/cerenkov/setTrackSecondariesFirst" not in macro_text


def test_generate_macro_emits_combined_track_secondaries_first(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_track_secondaries_first = True
    state.environment.scintillation_track_secondaries_first = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "track-first-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/optical/cerenkov/setTrackSecondariesFirst true" in macro_text
    assert "/process/optical/scintillation/setTrackSecondariesFirst true" in macro_text


def test_generate_macro_omits_track_secondaries_first_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = True
    state.environment.cerenkov_track_secondaries_first = False
    state.environment.scintillation_track_secondaries_first = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "track-first-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/initialize" in macro_text
    assert "/process/optical/cerenkov/setTrackSecondariesFirst" not in macro_text
    assert "/process/optical/scintillation/setTrackSecondariesFirst" not in macro_text


def test_generate_macro_omits_track_secondaries_first_when_optical_physics_off(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.optical_physics = False
    state.environment.cerenkov_track_secondaries_first = True
    state.environment.scintillation_track_secondaries_first = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "track-first-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/optical/cerenkov/setTrackSecondariesFirst" not in macro_text
    assert "/process/optical/scintillation/setTrackSecondariesFirst" not in macro_text
