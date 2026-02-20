"""Smart CAD classifier scaffolding for Phase 3.

This module defines a stable classifier contract for STEP-imported solids.
In v1 (skeleton), primitive detection is conservative and defaults to
`tessellated` unless an explicit classification hint is present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


ALLOWED_CLASSIFICATIONS = {
    "box",
    "cylinder",
    "sphere",
    "cone",
    "torus",
    "tessellated",
}


@dataclass
class SmartCadCandidate:
    """Classifier output contract for one imported source solid."""

    source_id: str
    classification: str
    confidence: float
    params: Dict[str, Any] = field(default_factory=dict)
    fallback_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "classification": self.classification,
            "confidence": self.confidence,
            "params": self.params,
            "fallback_reason": self.fallback_reason,
        }


def _normalize_classification(classification: Optional[str]) -> str:
    value = (classification or "tessellated").strip().lower()
    return value if value in ALLOWED_CLASSIFICATIONS else "tessellated"


def _clamp_confidence(confidence: Any) -> float:
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return 0.0
    if c < 0.0:
        return 0.0
    if c > 1.0:
        return 1.0
    return c


def build_candidate(
    source_id: str,
    classification: Optional[str] = "tessellated",
    confidence: Any = 0.0,
    params: Optional[Dict[str, Any]] = None,
    fallback_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds a normalized candidate dictionary using the classifier contract."""

    normalized_class = _normalize_classification(classification)
    normalized_conf = _clamp_confidence(confidence)

    # Non-tessellated classifications should not carry fallback reasons.
    if normalized_class != "tessellated":
        fallback_reason = None
    elif not fallback_reason:
        fallback_reason = "no_primitive_match_v1"

    candidate = SmartCadCandidate(
        source_id=source_id,
        classification=normalized_class,
        confidence=normalized_conf,
        params=params or {},
        fallback_reason=fallback_reason,
    )
    return candidate.to_dict()


def classify_shape(shape: Any, source_id: str) -> Dict[str, Any]:
    """Classifies a shape into primitive candidate schema.

    Skeleton behavior:
    - If a shape carries `airpet_classification_hint` / `_airpet_classification_hint`,
      we trust it (for tests and controlled internal adapters).
    - Otherwise returns conservative tessellated fallback.
    """

    hint = getattr(shape, "airpet_classification_hint", None)
    if hint is None:
        hint = getattr(shape, "_airpet_classification_hint", None)

    if hint is not None:
        # Hint can be a simple classification string or a dict payload.
        if isinstance(hint, str):
            return build_candidate(
                source_id=source_id,
                classification=hint,
                confidence=1.0,
                params={},
                fallback_reason=None,
            )
        if isinstance(hint, dict):
            return build_candidate(
                source_id=source_id,
                classification=hint.get("classification", "tessellated"),
                confidence=hint.get("confidence", 1.0),
                params=hint.get("params", {}),
                fallback_reason=hint.get("fallback_reason"),
            )

    return build_candidate(
        source_id=source_id,
        classification="tessellated",
        confidence=0.0,
        params={},
        fallback_reason="no_primitive_match_v1",
    )


def classify_candidates(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch classification helper for fixtures and pipeline tests.

    Each input item expects:
    - source_id: str
    - shape: Any (optional)
    """

    out: List[Dict[str, Any]] = []
    for item in items:
        source_id = str(item.get("source_id", "unknown_source"))
        out.append(classify_shape(item.get("shape"), source_id=source_id))
    return out


def summarize_candidates(candidates: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates an import-summary payload suitable for UI report scaffolding."""

    cands = list(candidates)
    total = len(cands)
    primitive_count = sum(1 for c in cands if c.get("classification") != "tessellated")
    tess_count = total - primitive_count

    counts_by_class = {key: 0 for key in ALLOWED_CLASSIFICATIONS}
    for c in cands:
        cls = _normalize_classification(c.get("classification"))
        counts_by_class[cls] += 1

    primitive_ratio = (primitive_count / total) if total else 0.0

    return {
        "total": total,
        "primitive_count": primitive_count,
        "tessellated_count": tess_count,
        "primitive_ratio": primitive_ratio,
        "counts_by_classification": counts_by_class,
    }
