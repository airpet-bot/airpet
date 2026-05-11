import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_field_propagation_round_trip():
    state = GeometryState()
    assert state.environment.field_stepper_type == ""
    assert state.environment.field_minimum_step_mm == 0.0

    state.environment.field_stepper_type = "ClassicalRK4"
    state.environment.field_minimum_step_mm = 10.0
    payload = state.to_dict()
    assert payload["environment"]["field_stepper_type"] == "ClassicalRK4"
    assert payload["environment"]["field_minimum_step_mm"] == 10.0

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.field_stepper_type == "ClassicalRK4"
    assert round_tripped.environment.field_minimum_step_mm == 10.0


def test_environment_state_validation_rejects_invalid_field_propagation_parameters():
    ok, err = EnvironmentState.validate({"field_stepper_type": 123})
    assert ok is False
    assert "field_stepper_type must be a string" in err

    ok, err = EnvironmentState.validate({"field_minimum_step_mm": "not-a-number"})
    assert ok is False
    assert "field_minimum_step_mm must be a number" in err


def test_project_json_save_load_persists_field_propagation_parameters():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.field_stepper_type = "DormandPrince745"
    pm.current_geometry_state.environment.field_minimum_step_mm = 0.01

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["field_stepper_type"] == "DormandPrince745"
    assert data["environment"]["field_minimum_step_mm"] == 0.01

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.field_stepper_type == "DormandPrince745"
    assert pm2.current_geometry_state.environment.field_minimum_step_mm == 0.01


def test_generate_macro_emits_field_stepper_type(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.field_stepper_type = "ClassicalRK4"
    state.environment.field_minimum_step_mm = 0.0

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "field-prop-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "# --- Field Propagation Parameters ---" in macro_text
    assert "/field/stepperType ClassicalRK4" in macro_text
    assert "/field/setMinimumStep" not in macro_text


def test_generate_macro_emits_field_minimum_step(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.field_stepper_type = ""
    state.environment.field_minimum_step_mm = 5.5

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "field-prop-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "# --- Field Propagation Parameters ---" in macro_text
    assert "/field/setMinimumStep 5.5 mm" in macro_text
    assert "/field/stepperType" not in macro_text


def test_generate_macro_emits_both_field_parameters(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.field_stepper_type = "DormandPrince745"
    state.environment.field_minimum_step_mm = 0.01

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "field-prop-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/field/stepperType DormandPrince745" in macro_text
    assert "/field/setMinimumStep 0.01 mm" in macro_text


def test_generate_macro_omits_field_propagation_parameters_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.field_stepper_type = ""
    state.environment.field_minimum_step_mm = 0.0

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "field-prop-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "# --- Field Propagation Parameters ---" not in macro_text
    assert "/field/stepperType" not in macro_text
    assert "/field/setMinimumStep" not in macro_text
