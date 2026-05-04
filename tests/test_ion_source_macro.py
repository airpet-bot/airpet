import json
from pathlib import Path

import pytest

from src.geometry_types import GeometryState, ParticleSource
from src.project_manager import ProjectManager
from src.expression_evaluator import ExpressionEvaluator


def _make_state_with_ion_source():
    state = GeometryState()
    source = ParticleSource(
        name="C14_ion",
        source_type="ion",
        ion_params={"Z": 6, "A": 14, "Q": 4, "excitation_energy_keV": 0.0},
        position={"x": "0", "y": "0", "z": "0"},
        rotation={"x": "0", "y": "0", "z": "0"},
        activity=1.0,
    )
    source._evaluated_position = {"x": 0, "y": 0, "z": 0}
    source._evaluated_rotation = {"x": 0, "y": 0, "z": 0}
    state.add_source(source)
    state.active_source_ids = [source.id]
    return state


def test_generate_macro_emits_ion_source_commands(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = _make_state_with_ion_source()

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "ion-source-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/gps/particle ion" in macro_text
    assert "/gps/ion 6 14 4 0.0" in macro_text
    # GPS source infrastructure should still be emitted
    assert "/gps/source/intensity" in macro_text
    # Position should still be emitted
    assert "/gps/pos/centre" in macro_text


def test_generate_macro_skips_gps_particle_for_ion_source(tmp_path):
    """If gps_commands contains a particle key for an ion source, it must be skipped."""
    pm = ProjectManager(ExpressionEvaluator())
    state = _make_state_with_ion_source()
    # Inject a spurious particle command
    source = list(state.sources.values())[0]
    source.gps_commands = {"particle": "proton", "energy": "100*keV"}

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "ion-source-skip-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    # Must contain ion, must NOT contain the spurious proton particle line
    assert "/gps/particle ion" in macro_text
    assert "/gps/ion 6 14 4 0.0" in macro_text
    assert "/gps/particle proton" not in macro_text
    # Energy can still be emitted because it's a valid GPS command for ions
    assert "/gps/energy 100.0 keV" in macro_text


def test_gps_source_still_works_after_ion_support(tmp_path):
    """Regression: a normal GPS source must still emit /gps/particle gamma etc."""
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    source = ParticleSource(
        name="gamma_source",
        gps_commands={"particle": "gamma", "energy": "100*keV"},
        position={"x": "0", "y": "0", "z": "0"},
        rotation={"x": "0", "y": "0", "z": "0"},
        activity=1.0,
    )
    source._evaluated_position = {"x": 0, "y": 0, "z": 0}
    source._evaluated_rotation = {"x": 0, "y": 0, "z": 0}
    state.add_source(source)
    state.active_source_ids = [source.id]

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "gps-source-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/gps/particle gamma" in macro_text
    assert "/gps/energy 100.0 keV" in macro_text
    assert "/gps/ion" not in macro_text


def test_ion_source_round_trip_via_dict():
    """ParticleSource must preserve ion_params through to_dict / from_dict."""
    source = ParticleSource(
        name="Fe56_ion",
        source_type="ion",
        ion_params={"Z": 26, "A": 56, "Q": 2, "excitation_energy_keV": 10.0},
    )
    data = source.to_dict()
    assert data["type"] == "ion"
    assert data["ion_params"] == {"Z": 26, "A": 56, "Q": 2, "excitation_energy_keV": 10.0}

    restored = ParticleSource.from_dict(data)
    assert restored.type == "ion"
    assert restored.ion_params == {"Z": 26, "A": 56, "Q": 2, "excitation_energy_keV": 10.0}
