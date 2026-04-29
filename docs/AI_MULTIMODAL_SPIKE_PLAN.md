# AI Multimodal Artifact Intake — Spike Plan

## Context

The multimodal artifact intake pipeline (checkpoints 1–9) is largely implemented:
- Artifact store with upload/list/get metadata routes
- Deterministic extraction schema and review-envelope generation
- Planning-envelope generation with diagnostic safeguards
- Execution bridge into `batch_geometry_update` AI tools
- Preflight cross-checks and Geant4-facing parity reports

The authoritative contract lives in `docs/AI_MULTIMODAL_ARTIFACT_INTAKE.md`.
This spike plan turns that contract into a concise, actionable reliability backlog.

## Goal

Make the multimodal intake workflow reliable enough for real detector-design
sketches (PDF/image → extracted dimensions → approved review → executed
geometry mutations) without silent failures or un-auditable state drift.

---

## Acceptance Criteria

### A. Artifact Store Routes (Checkpoint 1)
- [ ] `POST /api/ai/artifacts/upload` accepts PDF/PNG/JPEG/WebP and persists blob + manifest
- [ ] `GET|POST /api/ai/artifacts/list` returns deterministic sorted metadata and omits missing blobs by default
- [ ] `GET /api/ai/artifacts/<artifact_id>` returns exact metadata for a valid id
- [ ] All three routes return the documented error contracts (`404 artifact_not_found`, `409 artifact_blob_missing`)
- [ ] Route-level regression tests exist and pass without a running AI backend

### B. Extraction → Review → Planning → Execution End-to-End (Checkpoints 2–5)
- [ ] `POST /api/ai/artifacts/<id>/extraction/review` normalizes extraction and builds a review envelope
- [ ] `POST /api/ai/artifacts/<id>/planning/envelope` produces a ready/blocked planning envelope with diagnostics
- [ ] `POST /api/ai/artifacts/<id>/planning/execute` applies ready plans through `batch_geometry_update` and returns per-operation outcomes
- [ ] All error paths (missing artifact, stale blob, mismatched review, blocked planning) are covered by focused regression tests
- [ ] Existing schema tests (`test_ai_multimodal_extraction_schema.py`, `test_ai_multimodal_planning_schema.py`) continue to pass

### C. Preflight Invariant Cross-Check (Checkpoint 7)
- [ ] After execution, a preflight comparison (`baseline` vs `candidate`) is automatically run
- [ ] Mismatch classes are emitted for: `can_run` regression, issue-count regression, fingerprint drift
- [ ] Regression tests verify each mismatch class triggers under the correct conditions

### D. Geant4-Facing Parity Report (Checkpoints 8–9)
- [ ] Parity report includes operation-group rollups (`dimension_hints`, `material_updates`, `other_mutations`)
- [ ] Compatibility-confidence payload is deterministic (`label`, `score`, `reason_codes`)
- [ ] Issue-code family correlations map delta transitions to likely operation families
- [ ] Representative fixtures cover: success, partial failure, mismatch, mixed delta, procedural warning, failed-no-applied

### E. UI / Playwright Coverage
- [ ] A Playwright workflow uploads a small fixture PDF, builds extraction/review, runs planning/execute, and verifies the geometry hierarchy reflects the mutation
- [ ] Console error cleanliness is asserted (zero uncaught JS errors)
- [ ] The workflow works with local (vendored) browser dependencies

---

## Fixture Needs

### 1. Artifact Upload Fixtures
- `tests/fixtures/multimodal/upload/minimal.pdf` — single-page blank PDF (< 5 KB)
- `tests/fixtures/multimodal/upload/minimal.png` — small 100×100 PNG
- `tests/fixtures/multimodal/upload/minimal.jpg` — small JPEG
- `tests/fixtures/multimodal/upload/minimal.webp` — small WebP

### 2. Extraction Payload Fixtures
- `tests/fixtures/multimodal/extraction/valid_single_region.json` — one region, one dimension, one symbol
- `tests/fixtures/multimodal/extraction/confidence_out_of_range.json` — triggers validation error
- `tests/fixtures/multimodal/extraction/provenance_mismatch.json` — triggers provenance mismatch error

### 3. Planning / Execution Fixtures
Reuse the existing `examples/multimodal/` files where possible:
- `examples/multimodal/planning_execute_request.json`
- `examples/multimodal/planning_execute_request_partial_failure.json`
- `examples/multimodal/planning_execute_response_parity_mismatch.json`
- `examples/multimodal/planning_execute_response_parity_delta_mix.json`
- `examples/multimodal/planning_execute_response_parity_procedural_dimension_smoke.json`
- `examples/multimodal/planning_execute_response_parity_partial_failure_procedural_warning.json`
- `examples/multimodal/planning_execute_response_parity_failed_no_applied_warning.json`

Add one deterministic fixture specifically for route-level replay:
- `tests/fixtures/multimodal/replay/valid_execution_replay.json` — captures a full request/response pair for `planning/execute`

### 4. Playwright UI Fixtures
- `tests/fixtures/multimodal/ui/detector_sketch_small.pdf` — tiny PDF with a labeled rectangle and dimension
- `tests/fixtures/multimodal/ui/detector_sketch_small.png` — same content as PNG

---

## Test Gaps to Close

| Area | Current Coverage | Gap |
|------|------------------|-----|
| Artifact store routes | None | No tests for upload/list/get metadata |
| Extraction schema | `test_ai_multimodal_extraction_schema.py` (4 tests) | Good coverage; keep passing |
| Extraction/review route | `test_ai_multimodal_extraction_api.py` (3 route tests) | Good coverage; keep passing |
| Planning schema | `test_ai_multimodal_planning_schema.py` (3 tests) | Good coverage; keep passing |
| Planning/execute route | `test_ai_multimodal_extraction_api.py` (8 route tests) | Good coverage; keep passing |
| Playwright end-to-end | None | Need one workflow from upload → execute → hierarchy verification |

---

## Suggested Sequencing (if promoted)

1. **Artifact store route tests** — smallest coherent slice; no AI backend needed
2. **Playwright upload → execute smoke** — validates the full user-visible pipeline
3. **Preflight parity report focused regression** — hardens the Geant4-facing confidence signal
4. **Console error and error-contract audit** — ensures all failure paths surface useful diagnostics in the UI

## Out of Scope for This Spike

- Building new multimodal intake features beyond what is documented in `AI_MULTIMODAL_ARTIFACT_INTAKE.md`
- Changing the extraction/planning schema contracts
- Integrating with external AI vision APIs (the spike focuses on backend route reliability and UI workflow validation)

---

## Sign-off

This spike plan is complete when:
- [ ] This document is committed to `docs/AI_MULTIMODAL_SPIKE_PLAN.md`
- [ ] The fixture list above is acknowledged and any missing fixtures are created in subsequent tasks
- [ ] The test-gap table is referenced when the next multimodal reliability task is promoted to `NEXT`
