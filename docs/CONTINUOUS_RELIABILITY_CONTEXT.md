# AIRPET Continuous Reliability Context

## Purpose

This loop continuously improves AIRPET by dogfooding real user workflows and
turning failures into durable fixes. The goal is not to add broad new product
surface area each cycle. The goal is to make the existing product feel reliable,
self-contained, inspectable, and safe to use for Geant4 detector studies.

The loop should use Playwright MCP for browser validation whenever the task
touches user-visible behavior. Python, Node, and Geant4 tests should complement
the UI checks, not replace them when the risk is clearly interactive.

When the reliability backlog is exhausted, the loop may switch into bounded
Geant4 capability discovery. Discovery is not permission to invent arbitrary
work. It is a narrow process for comparing AIRPET against local Geant4 examples
and source, then seeding evidence-backed tasks with acceptance criteria.

## Current Product Need

AIRPET has accumulated substantial capability: AI-assisted geometry editing,
CAD import, detector feature generators, fields, scoring, simulation run
metadata, and analysis. The most valuable next work is reliability:

- first-load and project-load workflows must always show the expected geometry
  and hierarchy
- simulation and scoring workflows must fail gracefully and expose useful
  analysis state
- browser dependencies should be local so AIRPET works without CDN access
- high-value UI flows should have replayable Playwright coverage
- generated geometry, undo/redo, save/load, and reload should remain coherent
- debugging artifacts and temporary files should not become part of Git history

## Operating Rules

Work exactly one tracker item per run.

Before making changes:

- confirm the repo is on branch `dev`
- stop if HEAD is detached
- inspect `git status --short`
- ignore untracked files and ignored local scratch files
- stop if there are tracked changes outside docs for an unrelated in-progress
  human task
- being ahead of `origin/dev` is not a blocker

For each task:

- reproduce or inspect the workflow before editing when practical
- prefer small fixes that protect real user workflows
- add focused regression coverage
- use Playwright MCP for UI-facing work
- use the smallest sufficient non-UI tests for backend or pure JS helpers
- update `docs/CONTINUOUS_RELIABILITY_TRACKER.md`
- commit locally on `dev`
- do not attempt `git push`

If there is no `NEXT` task and no `PENDING` task:

- read `docs/GEANT4_CAPABILITY_DISCOVERY_GUIDE.md`
- perform exactly one Geant4 capability-discovery audit
- inspect one bounded Geant4 area under `ref/geant4-v11.3.2`
- compare it with AIRPET code, tests, and docs
- add at most three evidence-backed backlog tasks
- mark exactly one discovered task as `NEXT`
- do not implement the discovered task in the same run
- stop cleanly if no suitable task is found

Stop cleanly if:

- there is no `NEXT` task, no `PENDING` task, and discovery finds no admissible
  task
- Playwright cannot access a running AIRPET server and the task requires UI work
- the same task fails twice for the same reason
- the repo has conflicting tracked changes from a human or another agent

## External Runner Prompt

Use this prompt for an external automation runner:

```text
You are working on AIRPET in /Volumes/nvme/projects/airpet.

Read docs/CONTINUOUS_RELIABILITY_CONTEXT.md and docs/CONTINUOUS_RELIABILITY_TRACKER.md.
Work exactly one tracker item per run. Use the item marked NEXT, or promote the
highest-priority PENDING item if no NEXT item exists.

Before editing, verify that the repo is on branch dev and HEAD is not detached.
Inspect git status --short. Ignore untracked files and ignored local scratch
files, but stop if there are tracked changes outside docs that appear unrelated
to the current task or conflict with it. Being ahead of origin/dev is not a
blocker.

If there is no NEXT and no PENDING task, read
docs/GEANT4_CAPABILITY_DISCOVERY_GUIDE.md and perform exactly one bounded
Geant4 capability-discovery audit using the local tree at ref/geant4-v11.3.2.
Inspect one Geant4 capability area, compare it with AIRPET support, update the
tracker work log with evidence, and add at most three concrete G4CAP backlog
tasks. Mark exactly one as NEXT. Do not implement a task in the same run that
discovers it. If no admissible task is found, record that and stop.

For UI-facing tasks, use the Playwright MCP server to reproduce or validate the
workflow. For backend or pure JS helper work, run the smallest relevant Python,
Node, or Geant4 checks. Make the smallest coherent fix, add focused regression
coverage, update docs/CONTINUOUS_RELIABILITY_TRACKER.md with files changed,
tests run, outcome, and the next NEXT task, then commit locally on dev. Do not
push unless explicitly instructed by the human operator.

If blocked, update the tracker with BLOCKED status and the exact reason. Do not
invent unrelated new tasks.
```

## Playwright Expectations

Use the Playwright MCP server for browser checks. Prefer deterministic checks
over visual wandering:

- verify the default scene and hierarchy after first load
- capture console errors and fail on new uncaught JavaScript exceptions
- prefer stable selectors and visible text only when selectors are unavailable
- keep screenshots only when they explain a failure or document a UI state
- clean up test-created projects or give them unique names

If a dev server is not already running, start AIRPET using the project’s normal
local setup. If a server is already running, reuse it rather than starting a
second one.

## Useful Commands

Use the conda environment:

```bash
source setup_conda_env.sh
```

Common checks:

```bash
python3 -m py_compile app.py src/project_manager.py src/geometry_types.py
node --check static/main.js static/uiManager.js
python3 -m pytest tests/test_scoring_state.py -q
```

Geant4 app location:

```bash
geant4/build/airpet-sim
```

Preferred Geant4 install:

```bash
/Volumes/nvme/software/geant4/install
```

## Documentation Discipline

Keep this context stable. Put live progress in the tracker, not here. Update
this context only when the loop’s purpose, guardrails, or operating assumptions
change.
