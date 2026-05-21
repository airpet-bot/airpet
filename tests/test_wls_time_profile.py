"""Tests for WLS and WLS2 time profile persistence and macro emission (G4CAP-042)."""

import pytest
import json
from pathlib import Path

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


class TestWLSTimeProfile:
    """Regression tests for wls_time_profile and wls2_time_profile."""

    def test_round_trip_both_profiles(self):
        env = EnvironmentState(
            optical_physics=True,
            wls_time_profile="exponential",
            wls2_time_profile="delta",
        )
        d = env.to_dict()
        assert d["wls_time_profile"] == "exponential"
        assert d["wls2_time_profile"] == "delta"
        restored = EnvironmentState.from_dict(d)
        assert restored.wls_time_profile == "exponential"
        assert restored.wls2_time_profile == "delta"

    def test_round_trip_defaults(self):
        env = EnvironmentState()
        d = env.to_dict()
        assert d["wls_time_profile"] == ""
        assert d["wls2_time_profile"] == ""
        restored = EnvironmentState.from_dict(d)
        assert restored.wls_time_profile == ""
        assert restored.wls2_time_profile == ""

    def test_validation_rejects_non_string(self):
        ok, err = EnvironmentState.validate({"wls_time_profile": 123})
        assert not ok
        assert "must be a string" in err

    def test_project_json_persistence(self):
        pm = ProjectManager(ExpressionEvaluator())
        pm.current_geometry_state.environment.optical_physics = True
        pm.current_geometry_state.environment.wls_time_profile = "exponential"
        pm.current_geometry_state.environment.wls2_time_profile = "delta"
        json_string = pm.save_project_to_json_string()
        data = json.loads(json_string)
        assert data["environment"]["wls_time_profile"] == "exponential"
        assert data["environment"]["wls2_time_profile"] == "delta"

    def test_generate_macro_emits_wls_time_profile_when_optical_on(self, tmp_path):
        pm = ProjectManager(ExpressionEvaluator())
        state = GeometryState()
        state.environment.optical_physics = True
        state.environment.wls_time_profile = "exponential"
        state.environment.wls2_time_profile = "delta"

        version_dir = tmp_path / "version"
        version_dir.mkdir()
        (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

        macro_path = Path(
            pm.generate_macro_file(
                "test-job",
                {"events": 1},
                str(tmp_path),
                str(tmp_path),
                str(version_dir),
            )
        )
        macro_text = macro_path.read_text(encoding="utf-8")
        assert "/process/optical/wls/setTimeProfile exponential" in macro_text
        assert "/process/optical/wls2/setTimeProfile delta" in macro_text

    def test_generate_macro_omits_wls_at_defaults(self, tmp_path):
        pm = ProjectManager(ExpressionEvaluator())
        state = GeometryState()
        state.environment.optical_physics = True

        version_dir = tmp_path / "version"
        version_dir.mkdir()
        (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

        macro_path = Path(
            pm.generate_macro_file(
                "test-job",
                {"events": 1},
                str(tmp_path),
                str(tmp_path),
                str(version_dir),
            )
        )
        macro_text = macro_path.read_text(encoding="utf-8")
        assert "/process/optical/wls/setTimeProfile" not in macro_text
        assert "/process/optical/wls2/setTimeProfile" not in macro_text

    def test_generate_macro_omits_wls_when_optical_off(self, tmp_path):
        pm = ProjectManager(ExpressionEvaluator())
        state = GeometryState()
        state.environment.optical_physics = False
        state.environment.wls_time_profile = "exponential"
        state.environment.wls2_time_profile = "delta"

        version_dir = tmp_path / "version"
        version_dir.mkdir()
        (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

        macro_path = Path(
            pm.generate_macro_file(
                "test-job",
                {"events": 1},
                str(tmp_path),
                str(tmp_path),
                str(version_dir),
            )
        )
        macro_text = macro_path.read_text(encoding="utf-8")
        assert "/process/optical/wls/setTimeProfile" not in macro_text
        assert "/process/optical/wls2/setTimeProfile" not in macro_text

    def test_summary_dict_includes_profiles_when_optical_on(self):
        env = EnvironmentState(
            optical_physics=True,
            wls_time_profile="exponential",
            wls2_time_profile="delta",
        )
        summary = env.to_summary_dict()
        labels = [c["label"] for c in summary["active_controls"]]
        assert "WLS time profile" in labels
        assert "WLS2 time profile" in labels

    def test_summary_dict_omits_profiles_when_optical_off(self):
        env = EnvironmentState(
            optical_physics=False,
            wls_time_profile="exponential",
            wls2_time_profile="delta",
        )
        summary = env.to_summary_dict()
        labels = [c["label"] for c in summary["active_controls"]]
        assert "WLS time profile" not in labels
        assert "WLS2 time profile" not in labels
