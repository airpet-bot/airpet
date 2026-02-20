import json
from pathlib import Path

from src.smart_cad_classifier import (
    ALLOWED_CLASSIFICATIONS,
    build_candidate,
    classify_candidates,
    classify_shape,
    summarize_candidates,
)


class DummyShape:
    def __init__(self, hint=None):
        self.airpet_classification_hint = hint


def _fixture_cases():
    fixture_path = Path(__file__).parent / "fixtures" / "smart_cad" / "classifier_cases.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_build_candidate_normalization_and_confidence_clamping():
    c = build_candidate(
        source_id="s1",
        classification="NOT_A_REAL_CLASS",
        confidence=9.9,
        params={"x": 1},
    )

    assert c["source_id"] == "s1"
    assert c["classification"] == "tessellated"
    assert c["confidence"] == 1.0
    assert c["fallback_reason"] == "no_primitive_match_v1"


def test_classify_shape_defaults_to_tessellated():
    c = classify_shape(shape=object(), source_id="fallback_case")
    assert c["classification"] == "tessellated"
    assert c["fallback_reason"] == "no_primitive_match_v1"
    assert c["confidence"] == 0.0


def test_fixture_classifier_cases_contract_and_expectations():
    cases = _fixture_cases()

    items = []
    for case in cases:
        hint = case.get("hint")
        shape = DummyShape(hint=hint) if hint is not None else DummyShape()
        items.append({"source_id": case["source_id"], "shape": shape})

    candidates = classify_candidates(items)

    assert len(candidates) == len(cases)

    for case, candidate in zip(cases, candidates):
        # Contract checks
        assert set(candidate.keys()) == {
            "source_id",
            "classification",
            "confidence",
            "params",
            "fallback_reason",
        }
        assert candidate["classification"] in ALLOWED_CLASSIFICATIONS
        assert 0.0 <= candidate["confidence"] <= 1.0

        # Fixture expectations
        expected = case["expected"]
        assert candidate["classification"] == expected["classification"]
        assert candidate["fallback_reason"] == expected["fallback_reason"]


def test_summary_counts_and_ratio():
    candidates = [
        build_candidate("a", classification="box", confidence=0.9),
        build_candidate("b", classification="cylinder", confidence=0.8),
        build_candidate("c", classification="tessellated", confidence=0.0),
    ]

    summary = summarize_candidates(candidates)

    assert summary["total"] == 3
    assert summary["primitive_count"] == 2
    assert summary["tessellated_count"] == 1
    assert summary["primitive_ratio"] == 2 / 3
    assert summary["counts_by_classification"]["box"] == 1
    assert summary["counts_by_classification"]["cylinder"] == 1
    assert summary["counts_by_classification"]["tessellated"] == 1
