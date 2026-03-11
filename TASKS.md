# AIRPET Task Tracker

## In Progress

- None.

## Recently Completed

- **Cycle-report truncation diagnostics regression coverage (`max_cycles`)** (2026-03-11)
  - Added `_build_multi_cycle_lv_triangle(...)` test helper in `tests/test_preflight.py` to construct a deterministic multi-cycle LV graph for cap-behavior validation.
  - Added `test_find_preflight_hierarchy_cycles_respects_max_cycles_cap_deterministically` to lock `_find_preflight_hierarchy_cycles(..., max_cycles=...)` behavior:
    - deterministic cycle ordering
    - deterministic cap at `max_cycles`
    - deterministic `truncated=True` signaling when the cap is reached
  - Added `test_preflight_reports_cycle_truncation_issue_when_cycle_report_hits_cap` to lock emission of the `placement_hierarchy_cycle_report_truncated` info diagnostic from `run_preflight_checks()`.
  - Why: preserves debuggable, predictable failure-mode reporting when recursive geometry graphs produce many cycles.

- **Cycle-path diagnostics regression coverage for mixed physvol/procedural/assembly hierarchies** (2026-03-11)
  - Added `test_preflight_mixed_cycle_path_is_deterministic_and_deduplicated` in `tests/test_preflight.py` to lock deterministic cycle reporting for a mixed-edge loop:
    - `ASM → LV` via assembly placement
    - `LV → LV` via procedural container (`replica`)
    - `LV → ASM` via `physvol`
  - Test intentionally creates duplicate placements that collapse to the same graph edge and asserts only one `placement_hierarchy_cycle` issue is emitted, protecting de-duplication behavior.
  - Added `test_preflight_cycle_signature_normalization_deduplicates_rotations` to lock cycle-signature normalization for rotated representations of the same cycle.
  - Why: preserves deterministic, high-signal preflight diagnostics as mixed hierarchy graphs grow in complexity.

- **Placement hierarchy cycle detection now includes procedural-container edges** (2026-03-10)
  - Extended `_build_preflight_hierarchy_adjacency(...)` so procedural logical volumes (`replica`, `division`, `parameterised`) contribute deterministic LV→LV edges for cycle detection.
  - Added regression test `test_preflight_detects_procedural_placement_cycle` in `tests/test_preflight.py` covering recursive procedural-container loops.
  - Why: prevents recursive topology faults from escaping cycle diagnostics when loops are introduced through procedural containers instead of `physvol` placements.

- **Preflight guards for procedural placements (replica/division/parameterised)** (2026-03-10)
  - Added procedural preflight validation in `ProjectManager.run_preflight_checks()` for logical volumes using non-`physvol` content.
  - New checks include:
    - missing/unknown procedural `volume_ref`
    - world volume incorrectly used as a procedural child target
    - replica bounds sanity (`number`, `width`, non-zero direction)
    - division sanity (supported axis, partition bounds, derived slice width positivity for box mothers)
    - parameterised sanity (`ncopies` and parameter-block presence/count mismatch warning)
  - Added regression tests in `tests/test_preflight.py` for replica/division/parameterised invalid procedural configurations.
  - Why: catches stale procedural references and broken procedural bounds earlier, improving deterministic diagnostics before simulation/export.

- **Preflight version selection diagnostics: ordering + source metadata** (2026-03-10)
  - Added explicit ordering metadata across preflight version compare/list responses, including selection ordering basis for:
    - latest manual saved comparisons
    - autosave vs manual/snapshot comparisons
    - simulation-run-indexed manual comparison selectors
  - Added deterministic version source metadata in compare responses:
    - per-version source path checks (`version_dir_within_versions_root`, `version_json_within_versions_root`)
    - resolved version JSON mtime timestamps (`version_json_mtime_utc`)
    - timestamp provenance (`timestamp_from_version_id` for saved versions)
  - Expanded `list_preflight_versions` and run-id manual version listings with:
    - `ordering_basis` and root metadata
    - per-entry `timestamp_source`, `version_json_mtime_utc`, and source path checks
  - Added regression assertions in `tests/test_preflight.py` to lock ordering/source-metadata behavior.
  - Why: improves reproducibility and debugging by making version selection semantics explicit and auditable for both human users and AI agents.

- **Preflight cycle detection for LV/assembly placement hierarchy** (2026-03-10)
  - Added deterministic graph traversal in `ProjectManager.run_preflight_checks()` to detect recursive placement loops across:
    - logical volume → logical volume
    - logical volume ↔ assembly
    - assembly ↔ assembly
  - New preflight error code: `placement_hierarchy_cycle` with explicit cycle path diagnostics (e.g. `LV:A -> ASM:B -> LV:A`).
  - Added cycle de-duplication + deterministic ordering for stable summaries/fingerprints.
  - Added regression tests in `tests/test_preflight.py` for both LV↔LV and LV↔ASM loops.
  - Why: recursive placement loops are high-impact topology faults that can silently poison traversal/export logic and are hard to debug without explicit path-level reporting.

- **Preflight integrity hardening for world/placement references** (2026-03-10)
  - Added new preflight error checks for:
    - missing `world_volume_ref`
    - unknown `world_volume_ref`
    - missing placement `volume_ref`
    - unknown placement `volume_ref` (LV/assembly not found)
    - world volume incorrectly referenced as a child placement
  - Added regression tests in `tests/test_preflight.py` to lock behavior.
  - Why: these are simulation-blocking topology problems that should fail fast in deterministic preflight instead of surfacing later during run/export.

## Next Candidates

1. **Selection metadata consistency coverage across all preflight compare routes**
   - Add route-level regression checks to ensure `selection.ordering_basis` and source metadata remain stable across every compare endpoint variant.
   - Impact: medium (prevents drift/regression in reproducibility diagnostics contract).

2. **Cycle-diagnostics metadata enrichment for truncated reports**
   - Extend truncation reporting to include explicit cap metadata (e.g., `max_cycles`) and align helper/issue payloads for easier downstream debugging and AI-tool interpretation.
   - Impact: medium (improves failure-mode observability for complex recursive hierarchies).
