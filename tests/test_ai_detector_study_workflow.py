import json
import os
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

import h5py
import pytest

from app import (
    _detector_study_launch_gate,
    _list_persisted_simulation_runs,
    _reconcile_detector_study,
    app,
    dispatch_ai_tool,
    run_g4_simulation,
)
from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import Material
from src.project_manager import ProjectManager


GEANT4_EXECUTABLE = Path(__file__).resolve().parents[1] / "geant4" / "build" / "airpet-sim"


@pytest.fixture
def pm(tmp_path):
    manager = ProjectManager(ExpressionEvaluator())
    manager.projects_dir = str(tmp_path)
    manager.create_empty_project()
    return manager


def test_configure_detector_readout_resolves_physical_volume_and_marks_lv_sensitive(pm):
    target_pv = pm.current_geometry_state.logical_volumes["World"].content[0]

    result, error = pm.configure_detector_readout(
        hit_selection_mode="triggered_events",
        target_physical_volumes=[target_pv.id],
        minimum_hit_count=2,
        hit_energy_threshold="100 keV",
    )

    assert error is None
    assert result["readout"] == {
        "hit_selection_mode": "triggered_events",
        "target_sensitive_detectors": [],
        "target_logical_volumes": [],
        "target_physical_volumes": ["box_PV"],
        "minimum_hit_count": 2,
        "hit_energy_threshold": "100 keV",
        "resolved_sensitive_logical_volumes": ["box_LV"],
        "mark_targets_sensitive": True,
    }
    assert pm.current_geometry_state.logical_volumes["box_LV"].is_sensitive is True
    defaults = pm.current_geometry_state.scoring.run_manifest_defaults
    assert defaults["save_hits"] is True
    assert defaults["save_hit_metadata"] is True
    assert defaults["hit_selection_mode"] == "triggered_events"
    assert defaults["hit_target_physical_volumes"] == ["box_PV"]
    assert defaults["hit_minimum_multiplicity"] == 2


def test_configure_detector_readout_can_preserve_existing_sensitivity(pm):
    target_pv = pm.current_geometry_state.logical_volumes["World"].content[0]

    result, error = pm.configure_detector_readout(
        hit_selection_mode="target_hits_only",
        target_physical_volumes=[target_pv.id],
        mark_targets_sensitive=False,
    )

    assert error is None
    assert result["readout"]["mark_targets_sensitive"] is False
    assert result["readout"]["resolved_sensitive_logical_volumes"] == ["box_LV"]
    assert pm.current_geometry_state.logical_volumes["box_LV"].is_sensitive is False


def test_detector_study_ledger_persists_across_project_manager_restart(tmp_path):
    manager = ProjectManager(ExpressionEvaluator())
    manager.projects_dir = str(tmp_path)
    manager.project_name = "persisted-study"
    manager.create_empty_project()

    study = manager.create_detector_study(
        goal="Build and test a silicon detector.",
        execution_mode="full_study",
        requirements=["Use G4_Si"],
        success_criteria=["Record at least one hit"],
    )
    manager.update_detector_study(
        study["study_id"],
        phase="BUILDING",
        status_message="Geometry construction started.",
    )

    restarted = ProjectManager(ExpressionEvaluator())
    restarted.projects_dir = str(tmp_path)
    restarted.project_name = "persisted-study"
    restored = restarted.get_detector_study()

    assert restored["study_id"] == study["study_id"]
    assert restored["phase"] == "BUILDING"
    assert restored["brief"]["requirements"] == ["Use G4_Si"]
    assert restored["brief"]["success_criteria"] == ["Record at least one hit"]
    assert restored["schema_version"] == 3
    assert restored["checkpoints"][0]["label"] == "Study intake baseline"


def test_full_study_launch_gate_tracks_visual_geometry_revision(pm):
    study = pm.create_detector_study(
        goal="Build and run a detector.",
        execution_mode="full_study",
    )

    initial_gate = _detector_study_launch_gate(
        pm,
        detector_study_id=study["study_id"],
    )
    assert initial_gate["allowed"] is False
    assert initial_gate["reason"] == "visual_verification_required"

    pm.record_detector_study_visual_verification(
        study["study_id"],
        {
            "success": True,
            "request_id": "visual-1",
            "packet_metadata": {"views": ["front", "side"]},
            "ai_attachments": [],
        },
    )
    verified_gate = _detector_study_launch_gate(
        pm,
        detector_study_id=study["study_id"],
    )
    assert verified_gate["allowed"] is True

    pm.record_detector_study_geometry_change(
        study["study_id"],
        "Moved a detector component.",
    )
    invalidated_gate = _detector_study_launch_gate(
        pm,
        detector_study_id=study["study_id"],
    )
    assert invalidated_gate["allowed"] is False
    assert invalidated_gate["geometry_revision"] == 1
    assert invalidated_gate["visual_verified_revision"] is None


def test_detector_study_preflight_repair_budget_is_bounded(pm):
    study = pm.create_detector_study(
        goal="Run a bounded repair study.",
        execution_mode="full_study",
    )
    failed_report = {
        "summary": {"can_run": False, "issue_count": 1},
        "issues": [{"severity": "error", "message": "Missing source"}],
    }

    first = pm.record_detector_study_preflight(
        study["study_id"],
        failed_report,
    )
    second = pm.record_detector_study_preflight(
        study["study_id"],
        failed_report,
    )
    exhausted = pm.record_detector_study_preflight(
        study["study_id"],
        failed_report,
    )

    assert first["phase"] == "PREFLIGHT"
    assert second["coordinator"]["repair_attempts"] == 2
    assert exhausted["phase"] == "NEEDS_ATTENTION"
    gate = _detector_study_launch_gate(
        pm,
        detector_study_id=study["study_id"],
    )
    assert gate["reason"] == "repair_budget_exhausted"


def test_detector_study_checkpoint_restore_recovers_geometry(pm):
    study = pm.create_detector_study(
        goal="Test phase checkpoint restore.",
        execution_mode="build_validate",
    )
    box = pm.current_geometry_state.solids["box_solid"]
    assert box.raw_parameters["x"] == "100"

    box.raw_parameters["x"] = "250"
    success, error = pm.recalculate_geometry_state()
    assert success, error
    pm.record_detector_study_geometry_change(
        study["study_id"],
        "Changed the box size.",
    )

    restored = pm.restore_detector_study_checkpoint(study["study_id"])

    assert pm.current_geometry_state.solids["box_solid"].raw_parameters["x"] == "100"
    assert restored["phase"] == "INTAKE"
    assert restored["simulation"] is None
    assert restored["analysis"] is None


def test_detector_study_reconcile_completes_with_automatic_analysis(pm):
    pm.project_name = "analysis-study"
    study = pm.create_detector_study(
        goal="Run a detector study.",
        execution_mode="full_study",
    )
    version_id = "version-analysis"
    job_id = "job-analysis"
    run_dir = Path(pm._get_version_dir(version_id)) / "sim_runs" / job_id
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({
            "job_id": job_id,
            "status": "Completed",
            "total_events": 5,
            "completed_at": "2026-06-10T12:00:00Z",
        }),
        encoding="utf-8",
    )
    with h5py.File(run_dir / "output.hdf5", "w") as output:
        hits = output.create_group("default_ntuples/Hits")
        hits.create_dataset("entries", data=[2])
        particle_names = hits.create_group("ParticleName")
        particle_names.create_dataset("pages", data=[b"gamma", b"e-"])

    running = pm.attach_simulation_to_detector_study(
        study["study_id"],
        job_id=job_id,
        version_id=version_id,
        total_events=5,
    )
    reconciled = _reconcile_detector_study(pm, running)

    assert reconciled["phase"] == "COMPLETE"
    assert reconciled["simulation"]["status"] == "Completed"
    assert reconciled["analysis"]["status"] == "Completed"
    assert reconciled["analysis"]["summary"]["total_hits"] == 2
    assert reconciled["analysis"]["summary"]["particle_breakdown"] == {
        "gamma": 1,
        "e-": 1,
    }
    assert reconciled["report"]["analysis"]["summary"]["total_hits"] == 2
    assert reconciled["report"]["ai_conclusion"] is None
    assert reconciled["coordinator"]["interpretation_status"] == "pending"


def test_detector_study_routes_create_and_continue_active_study(pm):
    pm.project_name = "route-study"
    app.config["TESTING"] = True
    with (
        app.test_client() as client,
        patch("app.get_project_manager_for_session", return_value=pm),
    ):
        created_response = client.post("/api/ai/studies/ensure", json={
            "goal": "Build a silicon slab.",
            "execution_mode": "build_validate",
            "attachments": [{
                "artifact_id": "diagram-1",
                "original_filename": "slab.png",
            }],
        })
        assert created_response.status_code == 200
        created = created_response.get_json()["study"]

        continued_response = client.post("/api/ai/studies/ensure", json={
            "goal": "Make the slab 2 mm thick.",
            "execution_mode": "build_validate",
            "study_id": created["study_id"],
        })
        assert continued_response.status_code == 200
        continued = continued_response.get_json()["study"]

        assert continued["study_id"] == created["study_id"]
        assert continued["phase"] == "BUILDING"
        assert continued["brief"]["user_requests"] == [
            "Build a silicon slab.",
            "Make the slab 2 mm thick.",
        ]
        assert continued["brief"]["attachments"] == [{
            "artifact_id": "diagram-1",
            "original_filename": "slab.png",
        }]

        pm.update_detector_study(
            created["study_id"],
            phase="COMPLETE",
            status_message="Initial study complete.",
        )
        followup_response = client.post("/api/ai/studies/ensure", json={
            "goal": "Explain the result.",
            "execution_mode": "build_validate",
            "study_id": created["study_id"],
        })
        assert followup_response.get_json()["study"]["study_id"] == created["study_id"]

        cleared_response = client.delete("/api/ai/studies/active")
        assert cleared_response.status_code == 200
        assert pm.active_detector_study_id is None


def test_detector_study_route_blocks_then_resolves_automatic_intake(pm):
    pm.project_name = "automatic-intake"
    app.config["TESTING"] = True
    with (
        app.test_client() as client,
        patch("app.get_project_manager_for_session", return_value=pm),
    ):
        created_response = client.post("/api/ai/studies/ensure", json={
            "goal": "Build a 4x4 detector array with 10 mm spacing and simulate it.",
            "execution_mode": "full_study",
        })
        assert created_response.status_code == 200
        created_payload = created_response.get_json()
        study = created_payload["study"]

        assert created_payload["requires_clarification"] is True
        assert study["phase"] == "INTAKE"
        assert len(study["intake"]["blocking_questions"]) == 3

        answers = {
            item["question_id"]: {
                "source_particle_energy": "511 keV gamma",
                "active_material": "silicon",
                "spacing_semantics": "center-to-center pitch",
            }[item["question_id"]]
            for item in study["intake"]["blocking_questions"]
        }
        resolved_response = client.patch(
            f"/api/ai/studies/{study['study_id']}",
            json={
                "action": "resolve_intake",
                "goal": study["brief"]["goal"],
                "requirements": study["brief"]["requirements"],
                "assumptions": study["brief"]["assumptions"],
                "success_criteria": study["brief"]["success_criteria"],
                "answers": answers,
            },
        )
        assert resolved_response.status_code == 200
        resolved = resolved_response.get_json()["study"]

        assert resolved["phase"] == "PLANNED"
        assert resolved["intake"]["status"] == "ready"
        assert any(
            requirement
            == "Use this particle source specification: 511 keV gamma."
            for requirement in resolved["brief"]["requirements"]
        )


def test_detector_study_route_rejects_partial_intake_answers(pm):
    pm.project_name = "partial-intake"
    app.config["TESTING"] = True
    with (
        app.test_client() as client,
        patch("app.get_project_manager_for_session", return_value=pm),
    ):
        created = client.post("/api/ai/studies/ensure", json={
            "goal": "Build a detector and run it.",
            "execution_mode": "full_study",
        }).get_json()["study"]
        first_question = created["intake"]["blocking_questions"][0]

        response = client.patch(
            f"/api/ai/studies/{created['study_id']}",
            json={
                "action": "resolve_intake",
                "answers": {
                    first_question["question_id"]: "1 MeV electron",
                },
            },
        )

        assert response.status_code == 400
        assert "Answer all blocking questions" in response.get_json()["error"]


@pytest.mark.parametrize(
    ("route_path", "expected_status"),
    [
        ("/api/ai/chat", 409),
        ("/api/ai/chat/stream", 200),
    ],
)
def test_ai_chat_routes_block_unresolved_study_intake(
    pm,
    route_path,
    expected_status,
):
    pm.project_name = "blocked-chat-intake"
    study = pm.create_detector_study(
        goal="Build a detector and run it.",
        execution_mode="full_study",
        intake={
            "status": "needs_clarification",
            "blocking_questions": [{
                "question_id": "source_particle_energy",
                "question": "What particle and energy should AIRPET simulate?",
                "answer": None,
                "resolved": False,
            }],
        },
    )
    app.config["TESTING"] = True
    with (
        app.test_client() as client,
        patch("app.get_project_manager_for_session", return_value=pm),
    ):
        response = client.post(route_path, json={
            "message": "Start building now.",
            "execution_mode": "full_study",
            "detector_study_id": study["study_id"],
        })

    assert response.status_code == expected_status
    if route_path.endswith("/stream"):
        payload_text = response.get_data(as_text=True)
        assert '"error_type": "study_clarification_required"' in payload_text
    else:
        payload = response.get_json()
        assert payload["error_type"] == "study_clarification_required"
        assert payload["blocking_questions"][0]["question_id"] == (
            "source_particle_energy"
        )


def test_detector_readout_macro_commands_round_trip_through_saved_version(pm, tmp_path):
    result, error = pm.configure_detector_readout(
        hit_selection_mode="target_hits_only",
        target_logical_volumes=["box_LV"],
        target_sensitive_detectors=["box_LV_SD"],
        minimum_hit_count=1,
        hit_energy_threshold="25 keV",
    )
    assert error is None
    assert result

    version_dir = tmp_path / "version"
    run_dir = tmp_path / "run"
    version_dir.mkdir()
    run_dir.mkdir()
    (version_dir / "version.json").write_text(
        pm.save_project_to_json_string(),
        encoding="utf-8",
    )

    macro_path = pm.generate_macro_file(
        "readout-job",
        {"events": 3},
        str(tmp_path),
        str(run_dir),
        str(version_dir),
    )
    macro_text = Path(macro_path).read_text(encoding="utf-8")
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))

    assert "/g4pet/run/hitSelectionMode target_hits_only" in macro_text
    assert "/g4pet/run/hitTargetSensitiveDetectors box_LV_SD" in macro_text
    assert "/g4pet/run/hitTargetLogicalVolumes box_LV" in macro_text
    assert "/g4pet/run/hitMinimumMultiplicity 1" in macro_text
    assert "/g4pet/run/hitEnergyThreshold 25 keV" in macro_text
    assert metadata["resolved_run_manifest"]["hit_selection_mode"] == "target_hits_only"


def test_ai_run_detector_study_configures_beam_readout_and_launches(pm, tmp_path):
    version_dir = tmp_path / "version-ai-study"
    version_dir.mkdir()
    pm.current_version_id = "version-ai-study"
    pm.is_changed = False

    with (
        patch.object(
            pm,
            "run_preflight_checks",
            return_value={"summary": {"can_run": True, "issue_count": 0}, "issues": []},
        ),
        patch.object(pm, "_get_version_dir", return_value=str(version_dir)),
        patch.object(
            pm,
            "save_project_version",
            return_value=("version-ai-study", None),
        ),
        patch.object(
            pm,
            "generate_macro_file",
            return_value=str(version_dir / "sim_runs" / "job" / "run.mac"),
        ) as generate_macro,
        patch("threading.Thread") as thread_class,
    ):
        thread_class.return_value.start.return_value = None
        result = dispatch_ai_tool(
            pm,
            "run_detector_study",
            {
                "incident_beam": {
                    "target": "box_PV",
                    "particle": "gamma",
                    "energy": "1 MeV",
                    "incident_axis": "+z",
                },
                "hit_selection_mode": "triggered_events",
                "minimum_hit_count": 1,
                "hit_energy_threshold": "10 keV",
                "events": 25,
                "threads": 2,
            },
        )

    assert result["success"] is True
    assert result["version_id"] == "version-ai-study"
    assert result["detector_study"]["incident_beam"]["target_pv_name"] == "box_PV"
    assert result["detector_study"]["readout"]["target_physical_volumes"] == ["box_PV"]
    assert pm.current_geometry_state.logical_volumes["box_LV"].is_sensitive is True
    assert len(pm.current_geometry_state.active_source_ids) == 1
    sim_params = generate_macro.call_args.args[1]
    assert sim_params["events"] == 25
    assert sim_params["threads"] == 2
    assert sim_params["hit_selection_mode"] == "triggered_events"
    assert sim_params["hit_energy_threshold"] == "10 keV"
    thread_class.return_value.start.assert_called_once()


def test_persisted_simulation_runs_are_discoverable_after_memory_state_is_lost(pm):
    version_dir = Path(pm._get_version_dir("version-persisted"))
    run_dir = version_dir / "sim_runs" / "job-persisted"
    run_dir.mkdir(parents=True)
    (run_dir / "output.hdf5").write_bytes(b"placeholder")
    (run_dir / "metadata.json").write_text(
        json.dumps({
            "job_id": "job-persisted",
            "timestamp": "2026-06-10T10:00:00Z",
            "completed_at": "2026-06-10T10:01:00Z",
            "status": "Completed",
            "total_events": 42,
        }),
        encoding="utf-8",
    )

    runs = _list_persisted_simulation_runs(pm)

    assert runs == [{
        "job_id": "job-persisted",
        "version_id": "version-persisted",
        "status": "Completed",
        "progress": 42,
        "total_events": 42,
        "timestamp": "2026-06-10T10:01:00Z",
        "output_available": True,
        "metadata_available": True,
    }]


def _run_readout_smoke_case(tmp_path, *, target_logical_volumes, target_detectors):
    manager = ProjectManager(ExpressionEvaluator())
    manager.create_empty_project()
    manager.current_geometry_state.add_material(
        Material(
            name="Silicon",
            Z_expr="14",
            A_expr="28.0855",
            density_expr="2.33",
            state="solid",
        )
    )
    detector_lv = manager.current_geometry_state.logical_volumes["box_LV"]
    detector_lv.material_ref = "Silicon"
    detector_lv.is_sensitive = True
    success, error = manager.recalculate_geometry_state()
    assert success, error

    source, error = manager.configure_incident_beam(
        target="box_PV",
        particle="e-",
        energy="100 keV",
        incident_axis="+z",
        offset="1*mm",
        mark_target_sensitive=True,
        activate=True,
    )
    assert error is None
    assert source

    readout, error = manager.configure_detector_readout(
        hit_selection_mode="target_hits_only",
        target_logical_volumes=target_logical_volumes,
        target_sensitive_detectors=target_detectors,
        hit_energy_threshold="1 eV",
    )
    assert error is None
    assert readout

    version_dir = tmp_path / "version"
    run_dir = tmp_path / "run"
    version_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    (version_dir / "version.json").write_text(
        manager.save_project_to_json_string(),
        encoding="utf-8",
    )
    manager.generate_macro_file(
        "readout-runtime-smoke",
        {"events": 5, "threads": 1, "seed1": 12345, "seed2": 67890},
        str(GEANT4_EXECUTABLE.parent),
        str(run_dir),
        str(version_dir),
    )

    env = os.environ.copy()
    env["G4PHYSICSLIST"] = "FTFP_BERT"
    completed = subprocess.run(
        [str(GEANT4_EXECUTABLE), "run.mac"],
        cwd=run_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    output_path = run_dir / "output.hdf5"
    if not output_path.exists():
        return 0
    with h5py.File(output_path, "r") as output:
        hits = output["default_ntuples/Hits"]
        entries = hits["entries"]
        return int(entries[0]) if entries.shape != () else int(entries[()])


@pytest.mark.skipif(
    not GEANT4_EXECUTABLE.exists(),
    reason="AIRPET Geant4 executable is not built.",
)
def test_geant4_runtime_applies_target_only_detector_filter(tmp_path):
    matching_hits = _run_readout_smoke_case(
        tmp_path / "matching",
        target_logical_volumes=["box_LV"],
        target_detectors=[],
    )
    rejected_hits = _run_readout_smoke_case(
        tmp_path / "rejected",
        target_logical_volumes=[],
        target_detectors=["unmatched_detector_SD"],
    )

    assert matching_hits > 0
    assert rejected_hits == 0


def test_parallel_merge_offsets_first_available_worker_output(tmp_path):
    run_dir = tmp_path / "parallel-run"
    run_dir.mkdir()
    (run_dir / "run.mac").write_text(
        "\n".join([
            "/analysis/setFileName output.hdf5",
            "/run/beamOn 3",
        ]),
        encoding="utf-8",
    )
    (run_dir / "metadata.json").write_text(
        json.dumps({"job_id": "parallel-filtered", "total_events": 3}),
        encoding="utf-8",
    )

    def make_process(command, cwd, **_kwargs):
        macro_name = command[1]
        if macro_name == "run_t1.mac":
            with h5py.File(Path(cwd) / "output_t1.hdf5", "w") as output:
                hits = output.create_group("default_ntuples/Hits")
                hits.create_dataset("entries", data=[1])
                event_ids = hits.create_group("EventID")
                event_ids.create_dataset("pages", data=[0], maxshape=(None,))
                edep = hits.create_group("Edep")
                edep.create_dataset("pages", data=[1.0], maxshape=(None,))

        process = MagicMock()
        process.stdout.readline.return_value = ""
        process.stderr.readline.return_value = ""
        process.wait.return_value = 0
        process.returncode = 0
        return process

    with (
        patch("app.get_geant4_env", return_value=os.environ.copy()),
        patch("app.subprocess.Popen", side_effect=make_process),
    ):
        run_g4_simulation(
            "parallel-filtered",
            str(run_dir),
            "/fake/airpet-sim",
            {"events": 3, "threads": 2, "seed1": 10, "seed2": 20},
        )

    with h5py.File(run_dir / "output.hdf5", "r") as output:
        event_ids = output["default_ntuples/Hits/EventID/pages"][:]
        assert event_ids.tolist() == [2]
