# AIRPET Detector Feature Generators Context

Last updated: 2026-04-08

## Roadmap Position

This is the current active post-workflow phase in `docs/POST_WORKFLOW_REFINEMENT_ROADMAP.md`.

Workflow refinement, physics-environment refinement, and CAD interoperability refinement are complete enough that detector-specific feature generators are now the highest-value next loop.

## Mission

Add detector-oriented geometry generators that cover common repeated real-world simulation tasks without turning AIRPET into a full sketch-based CAD system.

This phase starts with patterned drilled-hole workflows, then broadens into layered stacks, tiled sensor arrays, repeated channels, supports, and compact recipe-style detector helpers.

## Product Position

AIRPET should not try to replace mechanical CAD tools for arbitrary sketching, constraints, or deep kernel editing.

The stronger product position is:

- import complex one-off mechanical parts from CAD when needed
- generate common detector-specific repeated geometry directly inside AIRPET
- keep those generated features inspectable, editable, and automation-friendly
- preserve a clean bridge between geometry creation, simulation setup, and downstream analysis

This phase is about reusable detector geometry authoring, not full general-purpose CAD parity.

## Why This Phase Comes Next

Recent work has materially improved:

- workflow-level reliability and regression coverage
- field-aware simulation environment controls
- CAD import, provenance, and safe supported reimport

What still slows down real detector design in AIRPET is the amount of repetitive geometry setup that falls between primitive authoring and full CAD import:

- drilled hole arrays
- layered detector sandwiches and shields
- tiled sensors and repeated modules
- repeated channels, supports, and detector-specific cut patterns

These are exactly the kinds of workflows where AIRPET can be more useful than a generic CAD system without needing to become one.

## Current Ground Truth

As of 2026-04-08:

- AIRPET already supports primitive solids, boolean-solid recipes, logical-volume and placement editing, and detector ring arrays.
- AIRPET already has STEP import/reimport support for complex external CAD geometry.
- AIRPET does not yet have a first-class detector-feature-generator layer for patterned or repeated detector geometry workflows.
- Many detector-oriented features that users want today still require manual boolean construction, repetitive placement work, or external CAD authoring.

The most natural first generator is a patterned drilled-hole workflow because:

- it is common in detector supports, shields, and collimators
- users often need multiple variants with only spacing/count changes
- AIRPET already has boolean-solid infrastructure that can likely carry an MVP

## Scope

In scope:

- detector-specific patterned and repeated geometry generators
- saved-project contracts for generated features
- UI, backend, AI, and serialization support for selected generators
- focused regression fixtures and deterministic example assets
- reuse of existing boolean-solid and array-placement infrastructure where practical

Out of scope for this phase:

- full sketch-based CAD authoring
- broad mechanical-design tooling unrelated to detector simulation workflows
- generic freeform surface modeling
- broad scoring/analysis redesign unrelated to geometry generation

## Design Principles

Prefer:

- detector-focused generators over generic CAD ambitions
- explicit saved-state provenance for generated features
- parameterized generators that users can revise without rebuilding everything by hand
- generated geometry that remains inspectable in AIRPET's existing solids, LVs, and placements model
- narrow, deterministic MVP slices for each generator
- small example assets and regression fixtures

Avoid:

- generators that silently emit large geometry trees with no surviving edit context
- one-off hardcoded recipes that cannot be parameterized later
- mixing unrelated detector-generator themes into a single automation cycle
- deep kernel-style editing abstractions before the first few generators prove the value

## Candidate Capability Sequence

1. A saved-project detector-feature-generator contract and first patterned-hole generator.
2. A rectangular drilled-hole array MVP backed by existing boolean-solid machinery.
3. UI and AI support for creating, inspecting, and revising hole-pattern generators.
4. Circular or bolt-circle hole-pattern follow-ons and orientation controls.
5. Compact examples and regression coverage for patterned-hole workflows.
6. Layered detector-stack generator.
7. Tiled sensor-array generator.
8. Repeated support-rib, channel, and compact recipe helpers.

## Companion Docs

Use these as supporting context when relevant:

- `docs/POST_WORKFLOW_REFINEMENT_ROADMAP.md`
- `docs/CAD_INTEROPERABILITY_REFINEMENT_CONTEXT.md`
- `docs/CAD_INTEROPERABILITY_REFINEMENT_TRACKER.md`

## Definition Of Done

A detector-feature-generator task is only `DONE` when:

- the generated-feature behavior is represented in saved AIRPET state when appropriate
- the resulting geometry is deterministic enough to exercise in focused tests or fixtures
- the UI and/or AI surfaces expose the feature when needed
- the tracker records files changed, tests run, outcome, and the next task

## Likely Successor Phases

After this tracker is substantially complete, the next good phases are likely:

1. Advanced Scoring And Run Controls
2. Packaging, Reproducibility, And Templates
