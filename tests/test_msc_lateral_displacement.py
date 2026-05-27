import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_msc_lateral_displacement_round_trip():
    state = GeometryState()
    assert state.environment.msc_lateral_displacement is True
    assert state.environment.msc_mu_had_lateral_displacement is True

    state.environment.msc_lateral_displacement = False
    state.environment.msc_mu_had_lateral_displacement = False
    payload = state.to_dict()
    assert payload["environment"]["msc_lateral_displacement"] is False
    assert payload["environment"]["msc_mu_had_lateral_displacement"] is False

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.msc_lateral_displacement is False
    assert round_tripped.environment.msc_mu_had_lateral_displacement is False


def test_environment_state_validation_rejects_invalid_msc_lateral_displacement():
    ok, err = EnvironmentState.validate({"msc_lateral_displacement": "yes"})
    assert ok is False
    assert "msc_lateral_displacement must be a boolean" in err

    ok, err = EnvironmentState.validate({"msc_lateral_displacement": 1})
    assert ok is False
    assert "msc_lateral_displacement must be a boolean" in err


def test_environment_state_validation_rejects_invalid_msc_mu_had_lateral_displacement():
    ok, err = EnvironmentState.validate({"msc_mu_had_lateral_displacement": "yes"})
    assert ok is False
    assert "msc_mu_had_lateral_displacement must be a boolean" in err

    ok, err = EnvironmentState.validate({"msc_mu_had_lateral_displacement": 1})
    assert ok is False
    assert "msc_mu_had_lateral_displacement must be a boolean" in err


def test_project_json_save_load_persists_msc_lateral_displacement():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.msc_lateral_displacement = False
    pm.current_geometry_state.environment.msc_mu_had_lateral_displacement = False

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["msc_lateral_displacement"] is False
    assert data["environment"]["msc_mu_had_lateral_displacement"] is False

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.msc_lateral_displacement is False
    assert pm2.current_geometry_state.environment.msc_mu_had_lateral_displacement is False


def test_generate_macro_emits_msc_false_when_disabled(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.msc_lateral_displacement = False
    state.environment.msc_mu_had_lateral_displacement = False

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "msc-false-job",
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
    assert "/process/msc/LateralDisplacement false" in macro_text
    assert "/process/msc/MuHadLateralDisplacement false" in macro_text


def test_generate_macro_omits_msc_at_default(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    assert state.environment.msc_lateral_displacement is True
    assert state.environment.msc_mu_had_lateral_displacement is True

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

    assert "/process/msc/LateralDisplacement false" not in macro_text
    assert "/process/msc/MuHadLateralDisplacement false" not in macro_text


def test_generate_macro_emits_individual_msc_flags(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.msc_lateral_displacement = False
    state.environment.msc_mu_had_lateral_displacement = True

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "msc-mixed-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/process/msc/LateralDisplacement false" in macro_text
    assert "/process/msc/MuHadLateralDisplacement false" not in macro_text
