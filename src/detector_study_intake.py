import re
from copy import deepcopy
from datetime import datetime


MAX_BLOCKING_QUESTIONS = 3

_PARTICLE_PATTERNS = (
    ("gamma", r"\b(?:gamma|photon)s?\b"),
    ("e-", r"\b(?:electron|electrons)\b|(?<!\w)e-(?!\w)"),
    ("e+", r"\b(?:positron|positrons)\b|(?<!\w)e\+(?!\w)"),
    ("proton", r"\bprotons?\b"),
    ("neutron", r"\bneutrons?\b"),
    ("mu-", r"\b(?:muon|muons|mu-)\b"),
    ("alpha", r"\b(?:alpha|alphas)\b"),
)

_MATERIAL_PATTERNS = (
    ("G4_Si", r"\b(?:silicon|si detector|sipm|sipms)\b"),
    ("G4_KAPTON", r"\bkapton\b"),
    ("G4_Al", r"\b(?:aluminum|aluminium)\b"),
    ("G4_Pb", r"\b(?:lead|pb)\b"),
    ("G4_WATER", r"\bwater\b"),
    ("G4_AIR", r"\bair\b"),
    ("G4_Galactic", r"\b(?:vacuum|galactic)\b"),
    ("G4_BGO", r"\bbgo\b"),
    ("G4_LSO", r"\b(?:lso|lyso)\b"),
)

_DETECTOR_TERMS = re.compile(
    r"\b(?:detector|sensor|sipm|scintillator|crystal|photodiode|"
    r"photomultiplier|sensitive|calorimeter|tracker|strip|pixel)\w*\b",
    re.IGNORECASE,
)

_ARRAY_TERMS = re.compile(
    r"\b(?:array|matrix|grid|row|column|tile|tiled|pattern)\w*\b",
    re.IGNORECASE,
)

_SPACING_TERM = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:nm|um|micrometers?|mm|cm|m)\s+"
    r"(?:of\s+)?spacing\b",
    re.IGNORECASE,
)

_EXPLICIT_SPACING_SEMANTICS = re.compile(
    r"\b(?:pitch|center[- ]to[- ]center|centre[- ]to[- ]centre|"
    r"edge[- ]to[- ]edge|gap)\b",
    re.IGNORECASE,
)

_ENERGY_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:[-*]\s*)?(?:eV|keV|MeV|GeV|TeV)\b",
    re.IGNORECASE,
)

_DIMENSION_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:[-*]\s*)?"
    r"(?:nm|um|micrometers?|mm|cm|m)\b",
    re.IGNORECASE,
)

_EVENT_PATTERN = re.compile(
    r"\b(\d[\d,]*)\s+(?:events?|particles?|histories)\b",
    re.IGNORECASE,
)

_THREAD_PATTERN = re.compile(
    r"\b(\d+)\s+(?:threads?|workers?)\b",
    re.IGNORECASE,
)


def _timestamp():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _dedupe_strings(values):
    result = []
    seen = set()
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _first_pattern_value(text, patterns):
    for value, pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return value
    return None


def _all_pattern_values(text, patterns):
    return [
        value
        for value, pattern in patterns
        if re.search(pattern, text, re.IGNORECASE)
    ]


def _question(question_id, question, reason, answer_hint):
    return {
        "question_id": question_id,
        "question": question,
        "reason": reason,
        "answer_hint": answer_hint,
        "answer": None,
        "resolved": False,
    }


def build_detector_study_intake(
    goal,
    *,
    execution_mode,
    attachments=None,
    project_context=None,
):
    text = str(goal or "").strip()
    lowered = text.lower()
    normalized_mode = str(execution_mode or "build_validate").strip().lower()
    attachment_list = deepcopy(attachments if isinstance(attachments, list) else [])
    context = project_context if isinstance(project_context, dict) else {}
    existing_sources = list(context.get("active_source_ids") or [])
    existing_sensitive_volumes = list(
        context.get("sensitive_logical_volumes") or []
    )
    existing_materials = list(context.get("assigned_materials") or [])

    particle = _first_pattern_value(text, _PARTICLE_PATTERNS)
    energy_match = _ENERGY_PATTERN.search(text)
    energy = (
        re.sub(r"\s*[-*]\s*", " ", energy_match.group(0)).strip()
        if energy_match
        else None
    )
    materials = _all_pattern_values(text, _MATERIAL_PATTERNS)
    dimensions = _dedupe_strings(_DIMENSION_PATTERN.findall(text))
    event_match = _EVENT_PATTERN.search(text)
    thread_match = _THREAD_PATTERN.search(text)
    events = int(event_match.group(1).replace(",", "")) if event_match else None
    threads = int(thread_match.group(1)) if thread_match else None
    has_detector_target = bool(_DETECTOR_TERMS.search(text))
    references_existing_geometry = bool(re.search(
        r"\b(?:current|existing|already configured|loaded)\b",
        text,
        re.IGNORECASE,
    ))
    has_array = bool(_ARRAY_TERMS.search(text))
    ambiguous_spacing = bool(
        has_array
        and _SPACING_TERM.search(text)
        and not _EXPLICIT_SPACING_SEMANTICS.search(text)
    )

    requirements = []
    assumptions = []
    success_criteria = [
        "Geometry passes AIRPET preflight checks.",
        "Visual verification finds no obvious missing, duplicated, or misaligned components.",
    ]
    defaults = []

    if materials:
        requirements.append(
            "Use the explicitly requested material assignments: "
            + ", ".join(materials)
            + "."
        )
    elif existing_materials:
        assumptions.append(
            "Preserve the current project material assignments unless the request explicitly changes them."
        )
    if dimensions:
        requirements.append(
            "Preserve the explicitly stated dimensions: "
            + ", ".join(dimensions)
            + "."
        )
    if particle or energy:
        source_parts = [part for part in (particle, energy) if part]
        requirements.append(
            "Configure the requested particle source: "
            + " at ".join(source_parts)
            + "."
        )

    if normalized_mode == "full_study":
        if events is None:
            events = 1000
            defaults.append({
                "field": "simulation.events",
                "value": 1000,
                "reason": "No event count was specified.",
            })
            assumptions.append(
                "Use 1000 events for the initial simulation; this can be increased after review."
            )
        if threads is None:
            threads = 1
            defaults.append({
                "field": "simulation.threads",
                "value": 1,
                "reason": "No thread count was specified.",
            })
        if existing_sensitive_volumes and references_existing_geometry:
            readout_mode = "target_hits_only"
            assumptions.append(
                "Reuse the current sensitive logical volumes for detector hit recording: "
                + ", ".join(existing_sensitive_volumes)
                + "."
            )
            success_criteria.append(
                "The initial simulation records at least one hit in a configured sensitive detector."
            )
        elif has_detector_target:
            readout_mode = "target_hits_only"
            defaults.append({
                "field": "readout.mode",
                "value": readout_mode,
                "reason": "A detector or sensor was explicitly described.",
            })
            assumptions.append(
                "Treat the described active detector or sensor components as sensitive and record their hits."
            )
            success_criteria.append(
                "The initial simulation records at least one hit in an intended sensitive detector."
            )
        elif existing_sensitive_volumes:
            readout_mode = "target_hits_only"
            assumptions.append(
                "Reuse the current sensitive logical volumes for detector hit recording: "
                + ", ".join(existing_sensitive_volumes)
                + "."
            )
            success_criteria.append(
                "The initial simulation records at least one hit in a configured sensitive detector."
            )
        else:
            readout_mode = None
        success_criteria.append("The Geant4 simulation completes without a fatal error.")
    else:
        readout_mode = None
        if normalized_mode == "build_validate":
            assumptions.append(
                "Do not launch Geant4 until the user explicitly switches to a full study or requests a run."
            )

    blocking_questions = []
    if (
        normalized_mode == "full_study"
        and not existing_sources
        and (not particle or not energy)
    ):
        if not particle and not energy:
            prompt = "What particle type and energy should AIRPET simulate?"
            hint = "For example: 511 keV gamma, 1 MeV electron, or 150 MeV proton."
        elif not particle:
            prompt = f"What particle type should AIRPET use at {energy}?"
            hint = "For example: gamma, electron, proton, or neutron."
        else:
            prompt = f"What energy should AIRPET use for the {particle} source?"
            hint = "Include units, for example 511 keV or 1 MeV."
        blocking_questions.append(_question(
            "source_particle_energy",
            prompt,
            "Particle type and energy materially determine the Geant4 physics result.",
            hint,
        ))

    if (
        normalized_mode == "full_study"
        and not materials
        and not existing_materials
    ):
        blocking_questions.append(_question(
            "active_material",
            "What material should the active detector or primary simulated component use?",
            "Material selection changes particle interactions and deposited energy.",
            "Use a material name such as silicon, LYSO, BGO, water, aluminum, or lead.",
        ))

    if ambiguous_spacing:
        blocking_questions.append(_question(
            "spacing_semantics",
            "Does the stated spacing mean center-to-center pitch or the edge-to-edge gap?",
            "The two interpretations produce different array dimensions and placements.",
            "Answer with 'center-to-center pitch' or 'edge-to-edge gap'.",
        ))

    if (
        normalized_mode == "full_study"
        and not has_detector_target
        and not existing_sensitive_volumes
    ):
        blocking_questions.append(_question(
            "sensitive_target",
            "Which component should AIRPET treat as the sensitive detector for hit recording?",
            "AIRPET needs a detector target to configure meaningful readout.",
            "Name the component or describe which generated part should record hits.",
        ))

    blocking_questions = blocking_questions[:MAX_BLOCKING_QUESTIONS]
    status = "needs_clarification" if blocking_questions else "ready"
    now = _timestamp()
    return {
        "schema_version": 1,
        "status": status,
        "original_request": text,
        "created_at": now,
        "updated_at": now,
        "confirmed_at": None,
        "inferred": {
            "particle": particle,
            "energy": energy,
            "materials": materials,
            "dimensions": dimensions,
            "events": events,
            "threads": threads,
            "has_detector_target": has_detector_target,
            "references_existing_geometry": references_existing_geometry,
            "readout_mode": readout_mode,
            "attachment_count": len(attachment_list),
            "attachment_names": [
                item.get("original_filename")
                for item in attachment_list
                if isinstance(item, dict) and item.get("original_filename")
            ],
            "existing_active_source_ids": existing_sources,
            "existing_sensitive_logical_volumes": existing_sensitive_volumes,
            "existing_assigned_materials": existing_materials,
            "request_mentions_simulation": any(
                term in lowered
                for term in ("simulate", "simulation", "run", "events", "beam", "source")
            ),
        },
        "defaults_applied": defaults,
        "blocking_questions": blocking_questions,
        "suggested_brief": {
            "requirements": _dedupe_strings(requirements),
            "assumptions": _dedupe_strings(assumptions),
            "success_criteria": _dedupe_strings(success_criteria),
        },
    }


def resolve_detector_study_intake(
    intake,
    *,
    answers=None,
):
    normalized = deepcopy(intake if isinstance(intake, dict) else {})
    answer_map = answers if isinstance(answers, dict) else {}
    questions = []
    unresolved = []
    for raw_question in normalized.get("blocking_questions") or []:
        if not isinstance(raw_question, dict):
            continue
        question = deepcopy(raw_question)
        question_id = str(question.get("question_id") or "").strip()
        answer = str(answer_map.get(question_id) or question.get("answer") or "").strip()
        question["answer"] = answer or None
        question["resolved"] = bool(answer)
        questions.append(question)
        if not answer:
            unresolved.append(question_id)

    normalized["blocking_questions"] = questions
    normalized["status"] = "ready" if not unresolved else "needs_clarification"
    normalized["updated_at"] = _timestamp()
    normalized["confirmed_at"] = (
        normalized["updated_at"] if not unresolved else None
    )
    normalized["unresolved_question_ids"] = unresolved
    return normalized


def intake_answer_requirements(intake):
    requirements = []
    for question in (intake or {}).get("blocking_questions") or []:
        if not isinstance(question, dict):
            continue
        answer = str(question.get("answer") or "").strip()
        if not answer:
            continue
        question_id = question.get("question_id")
        prefixes = {
            "source_particle_energy": "Use this particle source specification",
            "active_material": "Use this active material specification",
            "spacing_semantics": "Interpret array spacing as",
            "sensitive_target": "Use this sensitive detector target",
        }
        prefix = prefixes.get(question_id, "Apply this clarified requirement")
        requirements.append(f"{prefix}: {answer}.")
    return _dedupe_strings(requirements)
