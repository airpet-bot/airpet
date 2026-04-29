# AIRPET Continuous Reliability Tracker

## Loop State

- Status: ACTIVE
- Current phase: continuous reliability and self-contained workflow hardening
- Active context: `docs/CONTINUOUS_RELIABILITY_CONTEXT.md`
- Cadence target: every 30 minutes

## Task Rules

1. Work the item marked `NEXT`.
2. If no item is marked `NEXT`, promote the highest-priority `PENDING` item.
3. Complete exactly one item per run.
4. Add or update tests before marking a task `DONE`.
5. Use Playwright MCP for UI-facing tasks.
6. Update the work log and choose the next `NEXT` task.
7. Do not append speculative tasks unless the tracker is nearly exhausted and
   the new task is directly supported by a reproduced workflow gap.

## Status Values

- `NEXT`: work this item next
- `PENDING`: queued and ready
- `BLOCKED`: cannot proceed; explain why in notes or work log
- `DONE`: completed with tests or documented validation
- `NOOP`: no code change needed after investigation

## Current NEXT Task

`ACR-004`: Add a save/load/reload Playwright workflow for project JSON with
sources, scoring meshes, and generated geometry.

## Backlog

| ID | Priority | Area | Task | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| ACR-002 | P0 | First Load | Add a Playwright baseline that verifies startup geometry, hierarchy, and console cleanliness | DONE | Protects the default box and hierarchy path that has regressed before |
| ACR-003 | P0 | Scoring | Add a Playwright scoring smoke that creates or loads a sensitive detector workflow, runs simulation, and verifies Analysis becomes available | DONE | Exercises GPS source, sensitive detector, scoring mesh, Geant4 run, and Analysis button enablement |
| ACR-004 | P1 | Project Load | Add a save/load/reload Playwright workflow for project JSON with sources, scoring meshes, and generated geometry | NEXT | Focus on state that GDML import/export alone cannot preserve |
| ACR-005 | P1 | Detector Generators | Add a Playwright create/undo/reload workflow for tiled sensor arrays and one boolean-cut generator | PENDING | Verify hierarchy, renderer, Solids panel, and stale-object cleanup |
| ACR-006 | P1 | CAD | Add a compact CAD import/reimport browser workflow using small STEP fixtures | PENDING | Verify the CAD imports panel appears only when relevant and does not break narrow sidebars |
| ACR-007 | P1 | Simulation UX | Improve simulation failure/warning surfacing and add regression coverage for nonfatal artifact warnings | PENDING | Runs should be `Completed` when Geant4 succeeds even if optional artifacts are missing |
| ACR-008 | P2 | Git Hygiene | Add or update local ignore guidance for Playwright logs, scratch GDML, verification output, and machine-local reference folders | PENDING | Keep working tree noise from confusing future agents |
| ACR-009 | P2 | AI Parity | Add one route-vs-AI parity workflow for a high-value operation covered by Playwright | PENDING | Prefer scoring or generator workflows |
| ACR-010 | P2 | Multimodal Prep | Turn `docs/AI_MULTIMODAL_ARTIFACT_INTAKE.md` into a small spike plan with acceptance criteria and fixture needs | PENDING | Prep only; do not build multimodal intake in this loop unless promoted later |

## Work Log

| Date | Task | Status | Summary |
| --- | --- | --- | --- |
| 2026-04-29 | Loop setup | DONE | Archived previous agent-loop docs, created continuous reliability context/tracker, and seeded the first backlog around offline UI dependencies plus Playwright-backed workflow validation. |
| 2026-04-29 | ACR-001 offline browser dependencies | DONE | Vendored Plotly, Marked, three.js, selected three.js addon modules, three-mesh-bvh, and three-bvh-csg under `static/vendor/`; switched `templates/index.html` to local static paths; updated README library notes. Next: ACR-002. |
| 2026-04-29 | ACR-002 startup baseline | DONE | Added `tests/test_startup_baseline.py` which opens AIRPET, creates a new geometry to reach the clean default state, verifies the hierarchy shows "World" and "box_PV (LV: box_LV)", checks the 3D canvas is visible, and asserts zero uncaught JS errors. Installed Playwright locally under `.local-packages/`; added `.local-packages/` to `.gitignore`; removed `/docs/` from `.gitignore` so tracker files can be committed. Test passes in 6.65s. Next: ACR-003. |
| 2026-04-29 | ACR-003 scoring smoke | DONE | Added `tests/test_scoring_smoke.py` which creates a new geometry, adds a GPS source, marks box_LV as a sensitive detector, adds a scoring mesh, runs a 10-event Geant4 simulation, and verifies the Analysis button becomes enabled with no uncaught JS errors. Test passes in ~10s. Also reinstalled greenlet in .local-packages/ for Python 3.10 compatibility. Next: ACR-004. |
