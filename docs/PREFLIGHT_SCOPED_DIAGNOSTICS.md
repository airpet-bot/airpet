# Scoped Preflight Drift Diagnostics (`check_scope` / `run_preflight_scope`)

This note defines the deterministic semantics for scoped preflight drift diagnostics returned by:

- Route: `POST /api/preflight/check_scope`
- AI wrapper: `run_preflight_scope`

Both surfaces return identical payload structure for:

- `summary_delta`
- `issue_family_correlations`

## `summary_delta` semantics

`summary_delta` partitions full-geometry issue totals into scoped and outside-scope buckets:

- `summary_delta.scope`: counts (`errors`, `warnings`, `infos`, `issue_count`) from the scoped report.
- `summary_delta.outside_scope`: `full_summary - scoped_summary` per stat key, clamped at `>= 0`.

## `issue_family_correlations` semantics

`issue_family_correlations` is derived from preflight `summary.counts_by_code` in both full and scoped reports.

### Top-level buckets

- `scope`: issue-code counts attributable to the scoped report.
- `outside_scope`: issue-code counts attributable to the outside-scope remainder (`full - scope`, clamped at `>= 0`).

Each bucket includes:

- `issue_count`: sum of its `counts_by_code` values.
- `issue_codes`: sorted issue-code list.
- `counts_by_code`: deterministic issue-code → count mapping.

### Family-class lists

- `scope_only_issue_codes`: sorted codes where `scope_count > 0` and `outside_scope_count == 0`.
- `outside_scope_only_issue_codes`: sorted codes where `outside_scope_count > 0` and `scope_count == 0`.
- `shared_issue_codes`: sorted codes where both counts are non-zero.

### `entries` list

`entries` is deterministically ordered by `issue_code` (ascending lexical sort over the union of full/scoped code sets).

Each entry includes:

- `issue_code`
- `scope_count`
- `outside_scope_count`
- `correlation`:
  - `scope`: code appears only in scoped diagnostics
  - `outside_scope`: code appears only outside scope
  - `shared`: code appears in both scoped and outside-scope diagnostics

## Representative scoped-drift payload

- `examples/preflight/scoped_preflight_drift_issue_family_correlations.json`

This fixture-backed example demonstrates mixed scoped vs outside-scope divergence with deterministic ordering and correlation classes.
