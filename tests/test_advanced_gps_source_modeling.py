import json
from pathlib import Path

from app import dispatch_ai_tool
from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import GeometryState, ParticleSource
from src.project_manager import ProjectManager


def _generate_macro_for_state(tmp_path, state):
    pm = ProjectManager(ExpressionEvaluator())
    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")
    return Path(
        pm.generate_macro_file(
            "advanced-gps-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    ).read_text(encoding="utf-8")


def _add_active_source(state, source):
    source._evaluated_position = {"x": 11, "y": 12, "z": 13}
    source._evaluated_rotation = {"x": 0, "y": 0, "z": 0}
    state.add_source(source)
    state.active_source_ids = [source.id]
    return source


def test_advanced_gps_state_round_trips_through_particle_source():
    source = ParticleSource(
        name="advanced_source",
        gps_commands={"particle": "gamma"},
        advanced_gps={
            "source_list": {"multiple_vertex": True, "flat_sampling": True},
            "control": {
                "time": "5 ns",
                "polarization": {"x": 0, "y": 1, "z": 0},
                "number": 2,
                "check_volume": False,
                "verbose": 1,
            },
            "position": {"type": "Beam", "sigma_x": "1 mm", "sigma_y": "2 mm"},
            "angular": {"type": "focused", "focuspoint": {"x": 0, "y": 0, "z": "100 mm"}},
            "energy": {"type": "Arb", "min": "1 keV", "max": "10 keV", "apply_ene_weight": True},
            "histograms": [
                {
                    "type": "energy",
                    "points": [{"upper": "1 keV", "weight": 0.2}, {"value": "10 keV 1.0"}],
                    "interpolation": "Lin",
                }
            ],
            "ion": {"excitation_level": 3},
        },
    )

    data = source.to_dict()
    assert data["advanced_gps"]["source_list"]["multiple_vertex"] is True
    assert data["advanced_gps"]["control"]["polarization"] == "0 1 0"
    assert data["advanced_gps"]["angular"]["ang/focuspoint"] == "0 0 100 mm"
    assert data["advanced_gps"]["histograms"][0]["points"] == ["1 keV 0.2", "10 keV 1.0"]

    restored = ParticleSource.from_dict(data)
    assert restored.advanced_gps == data["advanced_gps"]


def test_generate_macro_emits_structured_advanced_gps_sections(tmp_path):
    state = GeometryState()
    source = ParticleSource(
        name="advanced_gamma",
        gps_commands={"particle": "gamma", "energy": "1*MeV"},
        advanced_gps={
            "source_list": {"multiple_vertex": True, "flat_sampling": True},
            "control": {
                "time": "5 ns",
                "polarization": {"x": 0, "y": 1, "z": 0},
                "number": 2,
                "check_volume": False,
                "verbose": 1,
            },
            "position": {
                "type": "Beam",
                "sigma_x": "1 mm",
                "sigma_y": "2 mm",
            },
            "angular": {
                "type": "focused",
                "focuspoint": {"x": 0, "y": 0, "z": "100 mm"},
                "mintheta": "0 deg",
                "maxtheta": "10 deg",
            },
            "energy": {
                "type": "Arb",
                "min": "1 keV",
                "max": "10 keV",
                "apply_ene_weight": True,
            },
            "histograms": [
                {
                    "type": "energy",
                    "reset": True,
                    "points": ["1 keV 0.2", "10 keV 1.0"],
                    "interpolation": "Lin",
                },
                {
                    "type": "biasx",
                    "points": [[0, 0.5], [1, 1.0]],
                },
            ],
        },
    )
    _add_active_source(state, source)

    macro_text = _generate_macro_for_state(tmp_path, state)

    assert "/gps/source/multiplevertex true" in macro_text
    assert "/gps/source/flatsampling true" in macro_text
    assert "/gps/verbose 1" in macro_text
    assert "/gps/number 2" in macro_text
    assert "/gps/time 5 ns" in macro_text
    assert "/gps/polarization 0 1 0" in macro_text
    assert "/gps/checkVolume false" in macro_text
    assert "/gps/pos/type Beam" in macro_text
    assert "/gps/pos/sigma_x 1 mm" in macro_text
    assert "/gps/ang/type focused" in macro_text
    assert "/gps/ang/focuspoint 0 0 100 mm" in macro_text
    assert "/gps/ene/type Arb" in macro_text
    assert "/gps/ene/applyEneWeight true" in macro_text
    assert "/gps/hist/reset energy" in macro_text
    assert "/gps/hist/type energy" in macro_text
    assert "/gps/hist/point 1 keV 0.2" in macro_text
    assert "/gps/hist/inter Lin" in macro_text
    assert "/gps/hist/type biasx" in macro_text
    assert "/gps/hist/point 0 0.5" in macro_text
    assert "/gps/pos/centre 11 12 13 mm" in macro_text


def test_advanced_gps_numeric_position_vectors_default_to_mm(tmp_path):
    state = GeometryState()
    source = ParticleSource(
        name="numeric_vector_source",
        gps_commands={"particle": "gamma"},
        advanced_gps={
            "airpet_transform_mode": "structured",
            "position": {"type": "Point", "centre": {"x": 1, "y": 2, "z": 3}},
            "angular": {"type": "focused", "focuspoint": [4, 5, 6]},
        },
    )
    _add_active_source(state, source)

    macro_text = _generate_macro_for_state(tmp_path, state)

    assert "/gps/pos/centre 1 2 3 mm" in macro_text
    assert "/gps/ang/focuspoint 4 5 6 mm" in macro_text


def test_advanced_gps_structured_transform_mode_skips_airpet_transform(tmp_path):
    state = GeometryState()
    source = ParticleSource(
        name="structured_position",
        gps_commands={"particle": "gamma"},
        advanced_gps={
            "airpet_transform_mode": "structured",
            "position": {
                "type": "Point",
                "centre": {"x": 1, "y": 2, "z": "3 mm"},
            },
        },
    )
    _add_active_source(state, source)

    macro_text = _generate_macro_for_state(tmp_path, state)

    assert "/gps/pos/centre 1 2 3 mm" in macro_text
    assert "/gps/pos/centre 11 12 13 mm" not in macro_text


def test_ion_excitation_level_emits_ion_level_command(tmp_path):
    state = GeometryState()
    source = ParticleSource(
        name="ion_level",
        source_type="ion",
        ion_params={"Z": 26, "A": 56, "Q": 2, "excitation_level": 4},
        gps_commands={"energy": "100*keV"},
    )
    _add_active_source(state, source)

    macro_text = _generate_macro_for_state(tmp_path, state)

    assert "/gps/particle ion" in macro_text
    assert "/gps/ionLvl 26 56 2 4" in macro_text
    assert "/gps/ion 26 56" not in macro_text


def test_ai_manage_particle_source_accepts_advanced_gps_payload(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    result = dispatch_ai_tool(pm, "manage_particle_source", {
        "action": "create",
        "name": "AIAdvancedGPS",
        "gps_commands": {"particle": "gamma"},
        "advanced_gps": {
            "control": {"time": "2 ns", "polarization": {"x": 0, "y": 0, "z": 1}},
            "energy": {"type": "Gauss", "mono": "511 keV", "sigma": "5 keV"},
            "histograms": [{"type": "biase", "points": ["0 1", "1 2"]}],
        },
    })
    assert result["success"], result

    source = pm.current_geometry_state.sources["AIAdvancedGPS"]
    assert source.advanced_gps["control"]["time"] == "2 ns"
    assert source.advanced_gps["energy"]["ene/type"] == "Gauss"

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(pm.save_project_to_json_string(), encoding="utf-8")
    macro_text = Path(
        pm.generate_macro_file(
            "ai-advanced-gps-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    ).read_text(encoding="utf-8")

    assert "/gps/time 2 ns" in macro_text
    assert "/gps/polarization 0 0 1" in macro_text
    assert "/gps/ene/type Gauss" in macro_text
    assert "/gps/ene/mono 511 keV" in macro_text
    assert "/gps/hist/type biase" in macro_text
