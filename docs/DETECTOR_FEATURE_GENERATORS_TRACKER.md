# Detector Feature Generators Tracker

Last updated: 2026-04-09

## Mission

Incrementally add detector-oriented geometry generators that cover common repeated geometry workflows in AIRPET without turning the product into a full sketch-based CAD system.

## Scope

In scope:

- patterned drilled-hole generators
- layered detector stacks
- tiled sensor arrays
- repeated support-rib and channel generators
- compact detector recipe primitives such as shields, collimators, or coils

Out of scope for a single cycle:

- full CAD authoring
- broad unrelated geometry refactors
- multiple generator families in one run

## Operating Loop

Each refinement cycle should do exactly one backlog item:

1. Read this tracker and `docs/DETECTOR_FEATURE_GENERATORS_CONTEXT.md`.
2. Pick the task marked `NEXT`.
3. If nothing is marked `NEXT`, pick the highest-priority `PENDING` task and mark it `NEXT`.
4. Implement that task end to end.
5. Add or update focused regression tests, example fixtures, or deterministic smoke checks.
6. Run the smallest sufficient test suite.
7. Update this tracker:
   - set the finished task to `DONE` or `BLOCKED`
   - add a short cycle-log entry
   - choose the next `NEXT` task
8. Stop after one task.

If blocked:

- record the blocker clearly
- mark the task `BLOCKED`
- nominate the next unblocked task as `NEXT`

## Definition Of Done

A task is only `DONE` when all of the following are true:

- the generator behavior exists in product code or saved-state contract as required
- focused regression, example, or smoke coverage passes locally
- any required UI and/or AI surfaces are updated to keep the feature usable
- this tracker records the outcome and next task

## Current Status

- Overall phase: roadmap phase R3, active
- Current priority: patterned-hole workflows first
- Success metric: a user can create at least one common detector-specific repeated geometry feature directly inside AIRPET and revise it without rebuilding the full geometry by hand

## Current NEXT Task

DFG-005: extend hole patterns to circular or bolt-circle layouts and orientation controls.

Focus for this task:

- keep the follow-on patterned-hole scope explicit instead of collapsing multiple pattern families into one change
- reuse the saved-state and realization model from the rectangular-hole MVP where it keeps the generator contract coherent
- land the smallest orientation-capable circular-pattern slice that stays deterministic enough for focused regression coverage

## Backlog

Statuses:

- `NEXT`
- `PENDING`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

| ID | Priority | Area | Feature | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| DFG-001 | P0 | Foundation | Add a saved-project detector-feature-generator contract and first patterned-hole generator specification | DONE | Saved-project `detector_feature_generators` entries now persist normalized rectangular drilled-hole-array specs, target refs, and realized-object placeholders |
| DFG-002 | P0 | Backend | Implement a rectangular drilled-hole array MVP backed by existing boolean-solid machinery | DONE | Rectangular drilled-hole generators now realize into reusable tube-cutter plus boolean-result solids and retarget matching logical volumes in place |
| DFG-003 | P1 | UI | Add UI surfaces to create, inspect, and revise patterned-hole generators | DONE | Landed as a properties-accordion card list plus a narrow modal/editor flow for rectangular drilled-hole generators |
| DFG-004 | P1 | AI | Add AI/backend tool surfaces for detector-feature-generator creation and inspection | DONE | Added a narrow `manage_detector_feature_generator` AI tool plus detector-generator inspection through shared component-details plumbing |
| DFG-005 | P1 | Feature | Extend hole patterns to circular or bolt-circle layouts and orientation controls | NEXT | Keep follow-on scope explicit instead of collapsing multiple pattern families into the MVP |
| DFG-006 | P1 | Examples | Add compact example assets and regression fixtures for patterned-hole workflows | PENDING | Favor small deterministic fixtures over large CAD-like examples |
| DFG-007 | P1 | Generator | Add a layered detector-stack generator | PENDING | Focus on absorber/sensor/support sandwiches and repeated module stacks |
| DFG-008 | P2 | Generator | Add a tiled sensor-array generator | PENDING | Useful for SiPM, pixel, and strip-style layouts |
| DFG-009 | P2 | Generator | Add repeated support-rib and channel generators | PENDING | Prefer practical repeated-cut or repeated-placement workflows over generic sketch tools |
| DFG-010 | P2 | Generator | Add compact detector recipe primitives for collimators, shields, or coils | PENDING | Keep the first recipe helpers bounded and detector-oriented |

## Cycle Log

| Date | Task | Outcome | Notes |
| --- | --- | --- | --- |
| 2026-04-08 | Backlog setup | DONE | Created the detector-feature-generators context and seeded the first active roadmap phase, starting with a saved-project detector-feature-generator contract and a narrow patterned-hole-generator MVP |
| 2026-04-08 | DFG-001 detector-feature-generator contract | DONE | Files: [`/Volumes/nvme/projects/airpet/src/geometry_types.py`](/Volumes/nvme/projects/airpet/src/geometry_types.py), [`/Volumes/nvme/projects/airpet/tests/test_detector_feature_generators_state.py`](/Volumes/nvme/projects/airpet/tests/test_detector_feature_generators_state.py), [`/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md`](/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md). Tests: `python3 -m py_compile src/geometry_types.py tests/test_detector_feature_generators_state.py`; `python3 -m pytest tests/test_detector_feature_generators_state.py -q`. Outcome: added a normalized saved-project `detector_feature_generators` contract with a first `rectangular_drilled_hole_array` specification, stable target/output object refs, and deterministic defaults/placeholders for future generated geometry. Next: DFG-002 |
| 2026-04-09 | DFG-002 rectangular drilled-hole realization | DONE | Files: [`/Volumes/nvme/projects/airpet/src/project_manager.py`](/Volumes/nvme/projects/airpet/src/project_manager.py), [`/Volumes/nvme/projects/airpet/tests/test_detector_feature_generators_state.py`](/Volumes/nvme/projects/airpet/tests/test_detector_feature_generators_state.py), [`/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md`](/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md). Tests: `python3 -m py_compile src/project_manager.py tests/test_detector_feature_generators_state.py`; `python3 -m pytest tests/test_detector_feature_generators_state.py -q`. Outcome: added a backend realization path that turns saved rectangular drilled-hole-array specs into reusable tube-cutter plus boolean-result solids, reuses those generated solids on rerun, retargets matching logical volumes in place, and records deterministic generated-object refs for follow-on UI work. Next: DFG-003 |
| 2026-04-09 | DFG-003 patterned-hole generator UI | DONE | Files: [`/Volumes/nvme/projects/airpet/app.py`](/Volumes/nvme/projects/airpet/app.py), [`/Volumes/nvme/projects/airpet/src/geometry_types.py`](/Volumes/nvme/projects/airpet/src/geometry_types.py), [`/Volumes/nvme/projects/airpet/src/project_manager.py`](/Volumes/nvme/projects/airpet/src/project_manager.py), [`/Volumes/nvme/projects/airpet/static/apiService.js`](/Volumes/nvme/projects/airpet/static/apiService.js), [`/Volumes/nvme/projects/airpet/static/main.js`](/Volumes/nvme/projects/airpet/static/main.js), [`/Volumes/nvme/projects/airpet/static/uiManager.js`](/Volumes/nvme/projects/airpet/static/uiManager.js), [`/Volumes/nvme/projects/airpet/static/detectorFeatureGeneratorsUi.js`](/Volumes/nvme/projects/airpet/static/detectorFeatureGeneratorsUi.js), [`/Volumes/nvme/projects/airpet/static/detectorFeatureGeneratorEditor.js`](/Volumes/nvme/projects/airpet/static/detectorFeatureGeneratorEditor.js), [`/Volumes/nvme/projects/airpet/templates/index.html`](/Volumes/nvme/projects/airpet/templates/index.html), [`/Volumes/nvme/projects/airpet/tests/test_detector_feature_generators_state.py`](/Volumes/nvme/projects/airpet/tests/test_detector_feature_generators_state.py), [`/Volumes/nvme/projects/airpet/tests/js/detector_feature_generators_ui.test.mjs`](/Volumes/nvme/projects/airpet/tests/js/detector_feature_generators_ui.test.mjs), [`/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md`](/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md). Tests: `python3 -m py_compile app.py src/project_manager.py src/geometry_types.py tests/test_detector_feature_generators_state.py`; `node --check static/main.js`; `node --check static/uiManager.js`; `node --check static/detectorFeatureGeneratorsUi.js`; `node --check static/detectorFeatureGeneratorEditor.js`; `python3 -m pytest tests/test_detector_feature_generators_state.py -q`; `node --test tests/js/cad_import_ui.test.mjs tests/js/detector_feature_generators_ui.test.mjs`. Outcome: added a narrow detector-generator accordion with inspect/edit/regenerate cards, a modal flow to create and revise rectangular drilled-hole generators, and backend upsert/regenerate API surfaces that preserve generated-solid identity across revisions. Next: DFG-004 |
| 2026-04-09 | DFG-004 detector-generator AI/backend surfaces | DONE | Files: [`/Volumes/nvme/projects/airpet/src/ai_tools.py`](/Volumes/nvme/projects/airpet/src/ai_tools.py), [`/Volumes/nvme/projects/airpet/src/project_manager.py`](/Volumes/nvme/projects/airpet/src/project_manager.py), [`/Volumes/nvme/projects/airpet/app.py`](/Volumes/nvme/projects/airpet/app.py), [`/Volumes/nvme/projects/airpet/tests/test_ai_api.py`](/Volumes/nvme/projects/airpet/tests/test_ai_api.py), [`/Volumes/nvme/projects/airpet/tests/test_ai_integration.py`](/Volumes/nvme/projects/airpet/tests/test_ai_integration.py), [`/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md`](/Volumes/nvme/projects/airpet/docs/DETECTOR_FEATURE_GENERATORS_TRACKER.md). Tests: `python3 -m py_compile src/ai_tools.py src/project_manager.py app.py tests/test_ai_api.py tests/test_ai_integration.py`; `PYTHONPATH=/tmp/occ_stub:$PYTHONPATH /Users/marth/miniconda/envs/airpet/bin/pytest tests/test_ai_integration.py::test_detector_feature_generator_ai_schema_exposes_manage_and_inspect_tools tests/test_ai_api.py::test_ai_tool_manage_detector_feature_generator_and_get_component_details -q`. Outcome: added a narrow `manage_detector_feature_generator` AI tool, extended shared component-detail inspection to fetch detector generators by `generator_id` or name, resolved target refs back to deterministic id/name pairs, and exposed generator counts/names in the project summary for AI discovery. Next: DFG-005 |

## Notes For Future Reordering

- It is fine to reorder tasks if a lower-level generated-feature contract needs to land before a UI slice.
- Prefer generator slices that remove repetitive manual geometry work for detector users quickly.
- Keep the first generator family small enough that one automation cycle can plausibly finish one backlog item end to end.
- Reuse existing boolean-solid, placement, and array infrastructure whenever it keeps the model understandable.
