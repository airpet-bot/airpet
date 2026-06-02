import json
from pathlib import Path

from app import dispatch_ai_tool
from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import (
    EnvironmentState,
    Geant4SimulationControl,
    GeometryState,
    ParticleSource,
)
from src.project_manager import ProjectManager


def _write_version_state(tmp_path, state):
    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")
    return version_dir


def _generate_macro_for_state(tmp_path, state, sim_params=None):
    pm = ProjectManager(ExpressionEvaluator())
    version_dir = _write_version_state(tmp_path, state)
    return Path(
        pm.generate_macro_file(
            "geant4-sim-control-job",
            sim_params or {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    ).read_text(encoding="utf-8")


def test_geant4_simulation_control_round_trips_with_environment_state():
    env = EnvironmentState.from_dict({
        "simulation_control": {
            "geometry_overlap_test": {
                "enabled": True,
                "resolution": 1234,
                "tolerance_mm": 0.01,
                "verbosity": False,
                "recursion_depth": 2,
                "maximum_errors": 5,
                "check_parallel": True,
            },
            "physics_process_presets": [
                {"preset_id": "em_low_energy_detector", "enabled": True},
            ],
            "macro_commands": [
                {
                    "command_id": "min-kin",
                    "phase": "pre_init",
                    "command": "/process/eLoss/minKinEnergy",
                    "value": "100 eV",
                },
            ],
            "biasing_placeholders": [
                {
                    "placeholder_type": "importance_sampling",
                    "target": "shield_region",
                    "notes": "Future variance-reduction request.",
                },
            ],
            "fast_simulation_placeholders": [
                {
                    "placeholder_type": "gflash",
                    "target": "calorimeter_LV",
                    "particle": "e-",
                },
            ],
        }
    })

    payload = env.to_dict()
    assert payload["simulation_control"]["geometry_overlap_test"]["enabled"] is True
    assert payload["simulation_control"]["macro_commands"][0]["command"] == "/process/eLoss/minKinEnergy"

    restored = EnvironmentState.from_dict(payload)
    assert restored.simulation_control.geometry_overlap_test["resolution"] == 1234
    assert restored.simulation_control.physics_process_presets[0]["preset_id"] == "em_low_energy_detector"


def test_generate_macro_emits_overlap_presets_advanced_commands_and_placeholder_notes(tmp_path):
    state = GeometryState()
    state.environment.simulation_control = Geant4SimulationControl.from_dict({
        "geometry_overlap_test": {
            "enabled": True,
            "resolution": 321,
            "tolerance_mm": 0.025,
            "maximum_errors": 7,
            "check_parallel": True,
        },
        "physics_process_presets": [
            {"preset_id": "em_low_energy_detector", "enabled": True},
        ],
        "macro_commands": [
            {
                "command_id": "min-kin",
                "phase": "pre_init",
                "command": "/process/eLoss/minKinEnergy",
                "value": "100 eV",
                "comment": "Lower EM kinetic-energy floor for this study.",
            },
            {
                "command_id": "verbose",
                "phase": "post_init",
                "command": "/tracking/verbose",
                "value": "1",
            },
            {
                "command_id": "progress",
                "phase": "pre_beam",
                "command": "/run/printProgress",
                "value": "10",
            },
        ],
        "biasing_placeholders": [
            {"placeholder_type": "importance_sampling", "target": "shield_region"},
        ],
        "fast_simulation_placeholders": [
            {"placeholder_type": "gflash", "target": "calorimeter_LV", "particle": "e-"},
        ],
    })

    macro_text = _generate_macro_for_state(tmp_path, state)

    init_index = macro_text.index("/run/initialize")
    assert macro_text.index("/process/em/fluo true") < init_index
    assert macro_text.index("/process/eLoss/minKinEnergy 100 eV") < init_index
    assert macro_text.index("/tracking/verbose 1") > init_index
    assert "/geometry/test/resolution 321" in macro_text
    assert "/geometry/test/tolerance 0.025 mm" in macro_text
    assert "/geometry/test/maximum_errors 7" in macro_text
    assert "/geometry/test/check_parallel true" in macro_text
    assert "/geometry/test/run" in macro_text
    assert "# Biasing placeholder: importance_sampling target=shield_region" in macro_text
    assert "# Fast-simulation placeholder: gflash target=calorimeter_LV particle=e-" in macro_text
    assert macro_text.index("/run/printProgress 10") < macro_text.index("/run/beamOn 1")


def test_generate_macro_emits_ordered_repeated_advanced_gps_commands(tmp_path):
    state = GeometryState()
    source = ParticleSource(
        name="hist_source",
        gps_commands={"particle": "gamma", "ene/type": "Arb"},
        gps_command_sequence=[
            {"command": "hist/type", "value": "energy"},
            {"command": "hist/point", "value": "0 0"},
            {"command": "hist/point", "value": "1 1"},
            {"command": "hist/inter", "value": "Lin"},
        ],
        position={"x": "0", "y": "0", "z": "0"},
        rotation={"x": "0", "y": "0", "z": "0"},
    )
    source._evaluated_position = {"x": 0, "y": 0, "z": 0}
    source._evaluated_rotation = {"x": 0, "y": 0, "z": 0}
    state.add_source(source)
    state.active_source_ids = [source.id]

    macro_text = _generate_macro_for_state(tmp_path, state)

    assert macro_text.count("/gps/hist/point") == 2
    assert macro_text.index("/gps/hist/point 0 0") < macro_text.index("/gps/hist/point 1 1")
    assert macro_text.index("/gps/hist/type energy") < macro_text.index("/gps/hist/inter Lin")


def test_ai_tool_manage_simulation_control_updates_project_state():
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    overlap_res = dispatch_ai_tool(pm, "manage_simulation_control", {
        "action": "set_geometry_overlap_test",
        "enabled": True,
        "resolution": 456,
    })
    assert overlap_res["success"], overlap_res
    assert overlap_res["simulation_control"]["geometry_overlap_test"]["enabled"] is True
    assert overlap_res["simulation_control"]["geometry_overlap_test"]["resolution"] == 456

    preset_res = dispatch_ai_tool(pm, "manage_simulation_control", {
        "action": "set_process_preset",
        "preset_id": "em_precision_transport",
        "enabled": True,
    })
    assert preset_res["success"], preset_res
    preset_ids = {
        entry["preset_id"]
        for entry in preset_res["simulation_control"]["physics_process_presets"]
        if entry.get("enabled", True)
    }
    assert "em_precision_transport" in preset_ids

    disable_res = dispatch_ai_tool(pm, "manage_simulation_control", {
        "action": "set_process_preset",
        "preset_id": "em_precision_transport",
        "enabled": "false",
    })
    assert disable_res["success"], disable_res
    disabled_entry = next(
        entry
        for entry in disable_res["simulation_control"]["physics_process_presets"]
        if entry["preset_id"] == "em_precision_transport"
    )
    assert disabled_entry["enabled"] is False
