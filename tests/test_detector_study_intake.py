from src.detector_study_intake import (
    build_attachment_aware_policy,
    build_detector_study_intake,
    intake_answer_requirements,
    resolve_detector_study_intake,
)


def test_fully_specified_full_study_builds_ready_brief_with_safe_defaults():
    intake = build_detector_study_intake(
        (
            "Build an 8x8 matrix of silicon sensors on a Kapton board with "
            "10 mm center-to-center pitch. Irradiate it with 511 keV gamma rays."
        ),
        execution_mode="full_study",
        attachments=[{"original_filename": "detector.png"}],
    )

    assert intake["status"] == "ready"
    assert intake["blocking_questions"] == []
    assert intake["inferred"]["particle"] == "gamma"
    assert intake["inferred"]["energy"] == "511 keV"
    assert intake["inferred"]["materials"] == ["G4_Si", "G4_KAPTON"]
    assert intake["inferred"]["events"] == 1000
    assert intake["inferred"]["threads"] == 1
    assert intake["inferred"]["readout_mode"] == "target_hits_only"
    assert intake["inferred"]["attachment_names"] == ["detector.png"]
    assert any(
        item["field"] == "simulation.events"
        for item in intake["defaults_applied"]
    )
    assert any(
        "at least one hit" in criterion
        for criterion in intake["suggested_brief"]["success_criteria"]
    )


def test_full_study_limits_blocking_questions_to_high_impact_decisions():
    intake = build_detector_study_intake(
        "Make a 4x4 array with 10 mm of spacing and run a simulation.",
        execution_mode="full_study",
    )

    assert intake["status"] == "needs_clarification"
    assert len(intake["blocking_questions"]) == 3
    assert [
        item["question_id"]
        for item in intake["blocking_questions"]
    ] == [
        "source_particle_energy",
        "active_material",
        "spacing_semantics",
    ]


def test_build_validate_does_not_require_simulation_source_details():
    intake = build_detector_study_intake(
        "Build a custom detector housing from the attached drawing.",
        execution_mode="build_validate",
        attachments=[{"original_filename": "housing.pdf"}],
    )

    assert intake["status"] == "ready"
    assert intake["blocking_questions"] == []
    assert intake["inferred"]["events"] is None
    assert intake["inferred"]["attachment_count"] == 1
    assert any(
        "Do not launch Geant4" in assumption
        for assumption in intake["suggested_brief"]["assumptions"]
    )
    assert intake["attachment_policy"]["intent"] == "reference_guided_construction"
    assert intake["attachment_policy"]["fidelity"] == "simulation_relevant_approximation"
    assert any(
        "references" in criterion
        for criterion in intake["attachment_policy"]["completion_checks"]
    )


def test_exact_attachment_reconstruction_requires_a_reference_scale():
    intake = build_detector_study_intake(
        "Reconstruct the attached connector exactly.",
        execution_mode="build_validate",
        attachments=[{"original_filename": "connector.png"}],
    )

    assert intake["status"] == "needs_clarification"
    assert [
        item["question_id"]
        for item in intake["blocking_questions"]
    ] == ["reference_scale"]

    resolved = resolve_detector_study_intake(
        intake,
        answers={"reference_scale": "The main tube outer diameter is 38 mm"},
    )
    assert intake_answer_requirements(resolved) == [
        "Use this reference scale: The main tube outer diameter is 38 mm.",
    ]


def test_attachment_policy_adapts_existing_geometry_without_becoming_a_mode():
    policy = build_attachment_aware_policy(
        "Import this CAD assembly and assign the highlighted sensor as sensitive.",
        [{"original_filename": "assembly.step"}],
    )

    assert policy["active"] is True
    assert policy["strategy"] == "evidence_guided_reconstruction"
    assert policy["intent"] == "reference_guided_adaptation"
    assert policy["attachment_names"] == ["assembly.step"]


def test_existing_project_assignments_avoid_redundant_full_study_questions():
    intake = build_detector_study_intake(
        "Run the current detector for 5000 events.",
        execution_mode="full_study",
        project_context={
            "active_source_ids": ["source-1"],
            "sensitive_logical_volumes": ["SensorLV"],
            "assigned_materials": ["G4_Si"],
        },
    )

    assert intake["status"] == "ready"
    assert intake["blocking_questions"] == []
    assert intake["inferred"]["events"] == 5000
    assert intake["inferred"]["existing_active_source_ids"] == ["source-1"]
    assert any(
        "Reuse the current sensitive logical volumes" in assumption
        for assumption in intake["suggested_brief"]["assumptions"]
    )


def test_intake_resolution_requires_all_answers_and_builds_requirements():
    intake = build_detector_study_intake(
        "Create an array with 5 mm spacing and simulate it.",
        execution_mode="full_study",
    )
    question_ids = [
        item["question_id"]
        for item in intake["blocking_questions"]
    ]

    partial = resolve_detector_study_intake(
        intake,
        answers={question_ids[0]: "511 keV gamma"},
    )
    assert partial["status"] == "needs_clarification"

    resolved = resolve_detector_study_intake(
        intake,
        answers={
            question_ids[0]: "511 keV gamma",
            question_ids[1]: "silicon",
            question_ids[2]: "center-to-center pitch",
        },
    )
    assert resolved["status"] == "ready"
    assert resolved["confirmed_at"]
    requirements = intake_answer_requirements(resolved)
    assert requirements == [
        "Use this particle source specification: 511 keV gamma.",
        "Use this active material specification: silicon.",
        "Interpret array spacing as: center-to-center pitch.",
    ]
