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
8. If no `NEXT` or `PENDING` tasks remain, use
   `docs/GEANT4_CAPABILITY_DISCOVERY_GUIDE.md` to run exactly one bounded
   Geant4 capability-discovery audit and seed at most three evidence-backed
   tasks.

## Status Values

- `NEXT`: work this item next
- `PENDING`: queued and ready
- `BLOCKED`: cannot proceed; explain why in notes or work log
- `DONE`: completed with tests or documented validation
- `NOOP`: no code change needed after investigation

## Current NEXT Task

Backlog exhausted. No remaining NEXT or PENDING tasks.

## Backlog

| ID | Priority | Area | Task | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| ACR-002 | P0 | First Load | Add a Playwright baseline that verifies startup geometry, hierarchy, and console cleanliness | DONE | Protects the default box and hierarchy path that has regressed before |
| ACR-003 | P0 | Scoring | Add a Playwright scoring smoke that creates or loads a sensitive detector workflow, runs simulation, and verifies Analysis becomes available | DONE | Exercises GPS source, sensitive detector, scoring mesh, Geant4 run, and Analysis button enablement |
| ACR-004 | P1 | Project Load | Add a save/load/reload Playwright workflow for project JSON with sources, scoring meshes, and generated geometry | DONE | Focus on state that GDML import/export alone cannot preserve |
| ACR-005 | P1 | Detector Generators | Add a Playwright create/undo/reload workflow for tiled sensor arrays and one boolean-cut generator | DONE | Verify hierarchy, renderer, Solids panel, and stale-object cleanup |
| ACR-006 | P1 | CAD | Add a compact CAD import/reimport browser workflow using small STEP fixtures | DONE | Verify the CAD imports panel appears only when relevant and does not break narrow sidebars |
| ACR-007 | P1 | Simulation UX | Improve simulation failure/warning surfacing and add regression coverage for nonfatal artifact warnings | DONE | Backend now distinguishes warnings from errors in stderr; frontend prefixes `[WARNING]` instead of `[ERROR]` for warning lines; status stays `Completed` when Geant4 succeeds with only nonfatal artifact warnings |
| ACR-008 | P2 | Git Hygiene | Add or update local ignore guidance for Playwright logs, scratch GDML, verification output, and machine-local reference folders | DONE | `.gitignore` updated; added `tests/test_gitignore_hygiene.py` to prevent accidental removal of ignore patterns |
| ACR-009 | P2 | AI Parity | Add one route-vs-AI parity workflow for a high-value operation covered by Playwright | DONE | Added `tests/test_route_ai_parity_detector_generators.py` covering tiled_sensor_array and channel_cut_array; both paths produce equivalent geometry state after normalizing volatile IDs |
| ACR-010 | P2 | Multimodal Prep | Turn `docs/AI_MULTIMODAL_ARTIFACT_INTAKE.md` into a small spike plan with acceptance criteria and fixture needs | DONE | Created `docs/AI_MULTIMODAL_SPIKE_PLAN.md` with acceptance criteria for artifact store routes, extraction→planning→execution end-to-end, preflight cross-checks, parity reports, and Playwright coverage; enumerated fixture needs (upload files, extraction payloads, replay fixtures, UI sketch fixtures); identified test gaps (no artifact store route tests, no Playwright end-to-end). No code changes.
| G4DISC-001 | P0 | Discovery | Run a bounded Geant4 capability-discovery audit and seed the next evidence-backed `G4CAP-*` backlog tasks | DONE | Inspected `ref/geant4-v11.3.2/examples/extended/persistency/gdml/G04`, `ref/geant4-v11.3.2/source/physics_lists/lists/src/`, and `ref/geant4-v11.3.2/examples/extended/runAndEvent/RE03`. Seeded three evidence-backed tasks. |
| G4CAP-001 | P1 | GDML | Emit and parse GDML `<auxiliary auxtype="SensDet">` tags so sensitive-detector assignments survive GDML round-trips | DONE | `src/gdml_writer.py` now emits `<auxiliary auxtype="SensDet" auxvalue=""/>` for sensitive LVs; `src/gdml_parser.py` parses it and sets `lv.is_sensitive = True`. Added `test_gdml_sensitive_detector_round_trip` in `tests/test_gdml.py`. |
| G4CAP-002 | P2 | Physics Lists | Expand the physics-list dropdown to include high-value missing lists (QBBC, QGSP_BERT_HP, QGSP_BIC, FTFP_BERT_ATL, QGSP_FTFP_BERT) | DONE | Added 5 new `<option>` values to `#simPhysicsList` in `templates/index.html`. Added `tests/test_physics_list_options.py` verifying each new list is accepted by `get_geant4_env` and forwarded to `G4PHYSICSLIST`; also guards existing lists and the omission case. |
| G4CAP-003 | P2 | Scoring | Emit `/score/create/boxMesh` and `/score/quantity/energyDeposit` macro commands for enabled scoring meshes, and instantiate `G4ScoringManager` in the C++ main | DONE | `src/project_manager.py` `generate_macro_file` now emits `/score/create/boxMesh`, `/score/mesh/boxSize`, `/score/mesh/translate/xyz`, `/score/mesh/nBin`, `/score/quantity/energyDeposit`, and `/score/close` for each enabled scoring mesh. `geant4/main.cc` now instantiates `G4ScoringManager`. Added `tests/test_scoring_macro_emission.py` with 2 tests verifying enabled mesh emission and disabled mesh omission. C++ compiles and links successfully. |

## Work Log

| Date | Task | Status | Summary |
| --- | --- | --- | --- |
| 2026-04-29 | Loop setup | DONE | Archived previous agent-loop docs, created continuous reliability context/tracker, and seeded the first backlog around offline UI dependencies plus Playwright-backed workflow validation. |
| 2026-04-29 | ACR-001 offline browser dependencies | DONE | Vendored Plotly, Marked, three.js, selected three.js addon modules, three-mesh-bvh, and three-bvh-csg under `static/vendor/`; switched `templates/index.html` to local static paths; updated README library notes. Next: ACR-002. |
| 2026-04-29 | ACR-002 startup baseline | DONE | Added `tests/test_startup_baseline.py` which opens AIRPET, creates a new geometry to reach the clean default state, verifies the hierarchy shows "World" and "box_PV (LV: box_LV)", checks the 3D canvas is visible, and asserts zero uncaught JS errors. Installed Playwright locally under `.local-packages/`; added `.local-packages/` to `.gitignore`; removed `/docs/` from `.gitignore` so tracker files can be committed. Test passes in 6.65s. Next: ACR-003. |
| 2026-04-29 | ACR-003 scoring smoke | DONE | Added `tests/test_scoring_smoke.py` which creates a new geometry, adds a GPS source, marks box_LV as a sensitive detector, adds a scoring mesh, runs a 10-event Geant4 simulation, and verifies the Analysis button becomes enabled with no uncaught JS errors. Test passes in ~10s. Also reinstalled greenlet in .local-packages/ for Python 3.10 compatibility. Next: ACR-004. |
| 2026-04-29 | ACR-004 save/load/reload | DONE | Added `tests/test_project_save_load_reload.py` which creates a new geometry, adds a GPS source, marks box_LV as sensitive, adds a scoring mesh, creates a rectangular drilled-hole generator on box_solid, exports the project JSON, reloads it via the hidden file input, and verifies that World, box_PV, the source, the scoring mesh, and the generator all persist with zero uncaught JS errors. Test passes in ~14s. Next: ACR-005. |
| 2026-04-29 | ACR-005 detector generator undo/reload | DONE | Added `tests/test_detector_generator_undo_reload.py` which creates a tiled sensor array generator on World, creates a channel cut array (boolean-cut) generator on box_solid, verifies both appear in the hierarchy, solids panel, and detector generators panel, undoes the channel cut creation, verifies stale boolean solids are cleaned up and box_solid is restored, reloads the page, and confirms the tiled sensor array persists with zero uncaught JS errors. Test passes in ~17s. Next: ACR-006. |
| 2026-04-29 | ACR-006 CAD import/reimport | DONE | Added `tests/test_cad_import_reimport.py` which creates a new geometry, verifies the CAD Imports accordion is hidden initially, imports `tests/fixtures/step/corpus/test_box.step`, verifies the panel appears with the import record and Reimport button, reimports `test_box_revised.step` via the panel reimport flow, verifies the record updates to the revised filename, and confirms other sidebar accordions remain functional with zero uncaught JS errors. Test passes in ~14s. Next: ACR-007. |
| 2026-04-29 | ACR-007 simulation warning surfacing | DONE | Updated `_build_simulation_log_payload` in `app.py` to treat stderr lines starting with `Warning:` as warnings (not errors), adding `has_warnings` to the log summary. Updated `pollSimStatus` in `static/main.js` to prefix `[WARNING]` instead of `[ERROR]` for warning lines. Added `test_simulation_status_api_distinguishes_warnings_from_errors` and `test_simulation_status_api_mixed_warnings_and_errors` to `tests/test_simulation_status_api.py`. All tests pass. Next: ACR-008. |
| 2026-04-29 | ACR-008 git ignore guidance | DONE | Updated `.gitignore` to ignore `.DS_Store`, `.playwright-mcp/`, root-level `test_*.yml` and `snapshot-*.md`, scratch GDML (`geant4/example_geometry.gdml`, `geant4/notes.txt`), `verification_run/`, and machine-local folders (`ref/`, `geom/`, `crysp/`). Verified `git status` no longer lists these artifacts. Next: ACR-009. |
| 2026-04-29 | ACR-008 git ignore guidance (test follow-up) | DONE | Added `tests/test_gitignore_hygiene.py` with 8 assertions covering Playwright artifacts, scratch GDML, verification output, machine-local folders, and `.DS_Store`. All tests pass. Fixed tracker `Current NEXT Task` header to ACR-009. Next: ACR-009. |
| 2026-04-29 | ACR-009 route-vs-AI parity | DONE | Added `tests/test_route_ai_parity_detector_generators.py` with two parity tests: `test_route_vs_ai_parity_tiled_sensor_array` and `test_route_vs_ai_parity_channel_cut_array`. Each test verifies that the direct Flask route (`/api/detector_feature_generators/upsert`) and the AI tool dispatch (`manage_detector_feature_generator`) produce equivalent geometry state. Comparison normalizes volatile object-ref `id` fields to focus on functional parity. All tests pass. Next: ACR-010. |
| 2026-04-29 | ACR-010 multimodal spike plan | DONE | Created `docs/AI_MULTIMODAL_SPIKE_PLAN.md` distilling `docs/AI_MULTIMODAL_ARTIFACT_INTAKE.md` into actionable acceptance criteria (artifact store routes, extraction→planning→execution, preflight cross-checks, parity reports, Playwright smoke) and enumerated fixture needs (upload files, extraction payloads, replay fixtures, UI sketch fixtures). Identified current test gaps: no artifact store route tests and no Playwright end-to-end coverage. No code changes. Backlog exhausted.
| 2026-04-29 | Self-expanding backlog setup | DONE | Added `docs/GEANT4_CAPABILITY_DISCOVERY_GUIDE.md`, updated the continuous-reliability context so an exhausted backlog triggers one bounded Geant4 capability-discovery audit, and seeded `G4DISC-001` as the next task. |
| 2026-04-29 | G4DISC-001 capability discovery | DONE | Inspected Geant4 `examples/extended/persistency/gdml/G04` (auxiliary SD info), `source/physics_lists/lists/src/` (~20 physics lists vs AIRPET's 5), and `examples/extended/runAndEvent/RE03` (command-based scoring meshes). Compared against AIRPET `src/gdml_writer.py`, `src/gdml_parser.py`, `templates/index.html`, `src/project_manager.py`, and `geant4/src/`. Found three concrete gaps and seeded `G4CAP-001` (GDML SD auxinfo), `G4CAP-002` (physics list expansion), and `G4CAP-003` (scoring mesh macro emission). Marked `G4CAP-001` as NEXT. |
| 2026-04-29 | G4CAP-001 GDML SD auxinfo round-trip | DONE | Updated `src/gdml_writer.py` to emit `<auxiliary auxtype="SensDet" auxvalue="{lv_name}"/>` inside `<volume>` for sensitive logical volumes. Updated `src/gdml_parser.py` to parse `<auxiliary auxtype="SensDet">` and set `lv.is_sensitive = True`. Added `test_gdml_sensitive_detector_round_trip` in `tests/test_gdml.py` verifying write, non-sensitive absence, and parse round-trip. Fixed duplicate auxiliary tag emission bug. All 31 tests in `tests/test_gdml.py` pass. Marked `G4CAP-002` as NEXT. |
| 2026-04-29 | G4CAP-002 physics list expansion | DONE | Added QBBC, QGSP_BERT_HP, QGSP_BIC, FTFP_BERT_ATL, and QGSP_FTFP_BERT to `#simPhysicsList` in `templates/index.html`. Added `tests/test_physics_list_options.py` with 3 tests covering acceptance of all 5 new lists, preservation of existing lists, and omission behavior. All tests pass. Marked `G4CAP-003` as NEXT. |
| 2026-04-29 | G4CAP-003 scoring mesh macro emission | DONE | Updated `src/project_manager.py` `generate_macro_file` to emit `/score/create/boxMesh`, `/score/mesh/boxSize`, `/score/mesh/translate/xyz`, `/score/mesh/nBin`, `/score/quantity/energyDeposit`, and `/score/close` for each enabled scoring mesh. Updated `geant4/main.cc` to instantiate `G4ScoringManager`. Added `tests/test_scoring_macro_emission.py` with 2 tests verifying enabled mesh emission and disabled mesh omission. C++ compiles and links successfully. Backlog exhausted. |
