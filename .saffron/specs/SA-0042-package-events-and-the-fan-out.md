---
id: SA-0042
title: PACKAGE's lines are strings and cannot reach the log the rest of the run writes
type: refactor
priority: 1
depends_on:
  - SA-0041
touches:
  - saffron/phases/package.py
  - saffron/cli.py
  - tests/test_package.py
  - tests/test_package_cell.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - tests/fixtures/watch-golden.txt
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - images/**
acceptance:
  - claim: >-
      Every `watch(...)` in `saffron/phases/package.py` and in
      `cli._resolve_stacked_on` is an `emit(<Event>)`, and no signature
      anywhere in `saffron/` still carries a `watch` parameter — a test greps
      the package and asserts none remains.
    witness: tests/test_cli.py::test_no_signature_in_the_package_still_takes_a_watch
  - claim: >-
      `saffron/cli.py` constructs the `emit` fan-out once and passes it to both
      `run_one_cell` and `package()`, so a task's PACKAGE events land in the
      same `events.jsonl` as the rest of its run.
    witness: tests/test_cli.py::test_package_events_land_in_the_runs_own_log
  - claim: >-
      The pull-request line reaches the log, not only the terminal. It is the
      line an unattended morning most needs about a task that reached PACKAGE.
    witness: tests/test_package.py::test_the_pull_request_url_is_logged_as_an_event
  - claim: >-
      The two `cell`-marked files in `touches` are migrated and run explicitly.
      `addopts` excludes them from `make check`, so the default suite cannot
      catch a migration that breaks them; say in the pull request body that
      `uv run pytest -m cell` was run against both.
    witness: tests/test_package_cell.py::test_package_emits_its_events_in_a_real_cell
  - claim: >-
      `run_one_cell` keeps a working default for callers passing no `emit`.
      Hoisting a fan-out into `cli.py` must not make the supervisor uncallable
      without one.
    witness: tests/test_events.py::test_run_one_cell_prints_without_an_emit_argument
    preserves: true
  - claim: >-
      The terminal output does not change, asserted against
      `tests/fixtures/watch-golden.txt` line for line.
    witness: tests/test_events.py::test_watch_output_matches_the_golden_fixture
    preserves: true
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
The second child of `SA-0031`, which died at 141 turns and $19.17 trying to do
both halves at once. `SA-0041` migrated the agent stream and deleted the
supervisor's adapter; this finishes the seam.

Measured against `saffron/SA-0030`'s head, 2026-09-01: `package.py` holds **8**
`watch(...)` call sites — re-verify, conflict, refusal-to-push, the pull request
URL — and `cli._resolve_stacked_on` takes `watch=print` and calls it **twice**.
Those two are the last `watch` outside `phases/`, added by `256e529`, a review
fix on `SA-0026` landed the day the design was written, on a spec whose own
`touches` named no `watch`. The design document says `cli.py` would never be
touched; that was true when written and false one commit later, and the code is
the authority.

`tests/test_package.py` carries 7 `watch=` sites, `tests/test_cli.py` 7, and
`tests/test_package_cell.py` 2.

## Problem
- **PACKAGE's events cannot reach the log while `emit` is built inside
  `run_one_cell`.** `package()` is called from `saffron/cli.py`, *outside* the
  supervisor, so its eight call sites fall back to `print` and none of the lines
  an unattended morning most needs — a refused push, a conflict with the default
  branch, new failures against `main`, the pull request URL — is recorded.
  This is why `package.py` and `cli.py` are one spec and not two.
- **Two of this spec's test files are `cell`-marked**, so `make check` never
  runs them and the suite will not catch a migration that breaks them.

## Out of scope
**Everything in `saffron/cli.py` except `_resolve_stacked_on`'s three lines and
the `emit` fan-out.** The file is in `touches` to finish the seam, not to be
refactored. `SA-0026` and `SA-0027` have both merged, so nothing races for it —
which is exactly why a wider edit here would be unforced.

**The three phase modules and the supervisor.** `SA-0041`'s, and `forbidden`
here.

**Changing any message**, and **any new event kind**, for the reasons `SA-0041`
gives.

## Notes for the agent
**Hoisting the fan-out into `cli.py` reverses a constraint the design argued
for, deliberately.** The design's reason for keeping the seam out of `cli.py`
was a collision with in-flight stacking work, and that expired when `SA-0026`
merged. The reason it now has to move is structural and does not expire:
PACKAGE runs outside `run_one_cell`, so a fan-out built inside the supervisor
can never see it. Building it one level up is the smaller of the two changes —
the alternative is moving PACKAGE inside `run_one_cell`, a different spec and
probably a worse design.

**`package.py` runs after the money is spent.** Its events are what an
unattended morning reads about a task that got all the way to PACKAGE and still
produced nothing mergeable. Do not economise on them.

**Run the `cell`-marked tests by hand and say so.** `uv run pytest -m cell
tests/test_package_cell.py` needs the images in `CLAUDE.md`. A criterion that
passes because its test was excluded is the failure `SA-0040` and `SA-0030`
both warned about.

**Every criterion names a witness and the `criteria` gate checks it** — absent
or failing at `base_sha`, green at head, except the two marked `preserves`,
which must be green at both.

Commit after each coherent step. Uncommitted work dies with the cell.
