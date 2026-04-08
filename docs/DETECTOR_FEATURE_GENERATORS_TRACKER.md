# Detector Feature Generators Tracker

Last updated: 2026-04-08

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

DFG-001: add a saved-project detector-feature-generator contract and the first patterned-hole generator specification.

Focus for this task:

- define how generated detector features are represented in saved AIRPET state
- make the first contract concrete enough to support a rectangular drilled-hole generator MVP
- keep the first generator narrow and deterministic enough to support focused regression coverage

## Backlog

Statuses:

- `NEXT`
- `PENDING`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

| ID | Priority | Area | Feature | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| DFG-001 | P0 | Foundation | Add a saved-project detector-feature-generator contract and first patterned-hole generator specification | NEXT | Start with a narrow contract that can support subtractive cylindrical hole arrays without overcommitting to a general CAD abstraction |
| DFG-002 | P0 | Backend | Implement a rectangular drilled-hole array MVP backed by existing boolean-solid machinery | PENDING | Prefer a box-oriented first slice with explicit count, pitch, diameter, depth, and target-solid references |
| DFG-003 | P1 | UI | Add UI surfaces to create, inspect, and revise patterned-hole generators | PENDING | Prefer a narrow modal/editor flow rather than a broad new side-panel system in the first slice |
| DFG-004 | P1 | AI | Add AI/backend tool surfaces for detector-feature-generator creation and inspection | PENDING | Keep the first AI contract aligned with the saved-state and UI generator model |
| DFG-005 | P1 | Feature | Extend hole patterns to circular or bolt-circle layouts and orientation controls | PENDING | Keep follow-on scope explicit instead of collapsing multiple pattern families into the MVP |
| DFG-006 | P1 | Examples | Add compact example assets and regression fixtures for patterned-hole workflows | PENDING | Favor small deterministic fixtures over large CAD-like examples |
| DFG-007 | P1 | Generator | Add a layered detector-stack generator | PENDING | Focus on absorber/sensor/support sandwiches and repeated module stacks |
| DFG-008 | P2 | Generator | Add a tiled sensor-array generator | PENDING | Useful for SiPM, pixel, and strip-style layouts |
| DFG-009 | P2 | Generator | Add repeated support-rib and channel generators | PENDING | Prefer practical repeated-cut or repeated-placement workflows over generic sketch tools |
| DFG-010 | P2 | Generator | Add compact detector recipe primitives for collimators, shields, or coils | PENDING | Keep the first recipe helpers bounded and detector-oriented |

## Cycle Log

| Date | Task | Outcome | Notes |
| --- | --- | --- | --- |
| 2026-04-08 | Backlog setup | DONE | Created the detector-feature-generators context and seeded the first active roadmap phase, starting with a saved-project detector-feature-generator contract and a narrow patterned-hole-generator MVP |

## Notes For Future Reordering

- It is fine to reorder tasks if a lower-level generated-feature contract needs to land before a UI slice.
- Prefer generator slices that remove repetitive manual geometry work for detector users quickly.
- Keep the first generator family small enough that one automation cycle can plausibly finish one backlog item end to end.
- Reuse existing boolean-solid, placement, and array infrastructure whenever it keeps the model understandable.
