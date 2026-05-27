import json
from pathlib import Path

import pytest

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_msc_step_limit_round_trip():
    state = GeometryState()
    assert state.environment.msc_step_limit == ""
    assert state.environment.msc_step_limit_mu_had == ""

    state.environment.msc_step_limit = "UseSafety"
    state.environment.msc_step_limit_mu_had = "Minimal"
    payload = state.to_dict()
    assert payload["environment"]["msc_step_limit"] == "UseSafety"
    assert payload["environment"]["msc_step_limit_mu_had"] == "Minimal"

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.msc_step_limit == "UseSafety"
    assert round_tripped.environment.msc_step_limit_mu_had == "Minimal"


def test_environment_state_validation_rejects_invalid_msc_step_limit():
    ok, err = EnvironmentState.validate({"msc_step_limit": 123})
    assert ok is False
    assert "msc_step_limit must be a string" in err

    ok, err = EnvironmentState.validate({"msc_step_limit": True})
    assert ok is False
    assert "msc_step_limit must be a string" in err


def test_environment_state_validation_rejects_invalid_msc_step_limit_mu_had():
    ok, err = EnvironmentState.validate({"msc_step_limit_mu_had": 123})
    assert ok is False
    assert "msc_step_limit_mu_had must be a string" in err

    ok, err = EnvironmentState.validate({"msc_step_limit_mu_had": True})
    assert ok is False
    assert "msc_step_limit_mu_had must be a string" in err


def test_project_json_save_load_persists_msc_step_limit():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.msc_step_limit = "UseSafety"
    pm.current_geometry_state.environment.msc_step_limit_mu_had = "Minimal"

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["msc_step_limit"] == "UseSafety"
    assert data["environment"]["msc_step_limit_mu_had"] == "Minimal"

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.msc_step_limit == "UseSafety"
    assert pm2.current_geometry_state.environment.msc_step_limit_mu_had == "Minimal"


def test_generate_macro_emits_msc_step_limit_when_set(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.msc_step_limit = "UseSafety"
    state.environment.msc_step_limit_mu_had = "Minimal"

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "msc-step-limit-job",
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
    assert "/process/msc/StepLimit UseSafety" in macro_text
    assert "/process/msc/StepLimitMuHad Minimal" in macro_text


def test_generate_macro_omits_msc_step_limit_at_default(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    assert state.environment.msc_step_limit == ""
    assert state.environment.msc_step_limit_mu_had == ""

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

    assert "/process/msc/StepLimit" not in macro_text
    assert "/process/msc/StepLimitMuHad" not in macro_text


def test_generate_macro_emits_individual_msc_step_limits(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.environment.msc_step_limit = "UseSafety"
    state.environment.msc_step_limit_mu_had = ""

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

    assert "/process/msc/StepLimit UseSafety" in macro_text
    assert "/process/msc/StepLimitMuHad" not in macro_text


def test_environment_state_summary_includes_msc_step_limit():
    state = GeometryState()
    state.environment.msc_step_limit = "UseSafety"
    state.environment.msc_step_limit_mu_had = "Minimal"

    summary = state.environment.to_summary_dict()
    assert summary["has_active_controls"] is True
    kinds = [c["kind"] for c in summary["active_controls"]]
    assert "msc_step_limit" in kinds
    assert "msc_step_limit_mu_had" in kinds
    assert "MSC step limit: UseSafety" in summary["summary_text"]
    assert "MSC step limit mu/had: Minimal" in summary["summary_text"]
