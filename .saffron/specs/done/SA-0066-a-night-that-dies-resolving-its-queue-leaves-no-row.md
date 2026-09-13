---
id: SA-0066
title: a night that dies resolving its queue leaves no row to say it ever began
type: bug
priority: 1
depends_on: []
touches:
  - saffron/cli.py
  - saffron/batch.py
  - tests/test_cli.py
  - tests/test_batch.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/ledger.py
  - saffron/preflight.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 5
max_attempts: 3
max_turns: 40
risk: standard
acceptance:
  - claim: >-
      A spec directory that discovery refuses while the queue is being resolved
      still leaves a batch row behind, closed `INFRASTRUCTURE`, and no task is
      started. Today the refusal propagates past `run_batch` to `main`'s
      catch-all, which prints one line and exits 2 with nothing in the ledger:
      the morning reads a night that never happened.
    witness: tests/test_cli.py::test_a_queue_discovery_refuses_still_leaves_a_closed_batch_row
  - claim: >-
      Any other exception raised while resolving the queue closes the row the
      same way. Resolution is an export at the pinned base, a reconcile against
      GitHub and a scan, and all three do real work that can fail. A refusal
      from discovery is only the case that was measured.
    witness: tests/test_cli.py::test_any_raise_resolving_the_queue_still_closes_the_batch_row
  - claim: >-
      The command exits 2 and says, on a line that starts `batch:`, that the
      queue could not be resolved, carrying the exception's own text. It must
      not say readiness failed. Readiness passed, and a line naming the wrong
      step sends the operator to re-check a token and a mirror that were fine.
      The witness asserts the line's `batch:` prefix, not only its text:
      `main`'s catch-all already prints the exception's text at base, on a
      `saffron:` line.
    witness: tests/test_cli.py::test_a_queue_that_cannot_be_resolved_says_so_on_the_batch_line
  - claim: >-
      A readiness failure still leaves an `INFRASTRUCTURE` row with its end
      time, and still prints `readiness failed at` the step and its detail.
    witness: tests/test_cli.py::test_an_unready_night_still_leaves_a_row_saying_it_was_attempted
    preserves: true
  - claim: >-
      A failed readiness still scans nothing. The order of the checks is §4.4's,
      and catching a failure in resolution must not move the scan ahead of
      readiness.
    witness: tests/test_cli.py::test_a_failed_readiness_still_scans_nothing
    preserves: true
---

## Context

`docs/BACKLOG.md` item **95**, filed by the review round on `SA-0065` (PR #185).
`SA-0065` made `discover_specs` refuse a spec directory that is absent or is not
a directory, so the silent empty queue of item **26** now stops the night
instead of draining it. That was right, and it moved the failure into a place
nothing records.

Traced at `a92571d`. `_batch` calls `_resolve_queue` inside its `readiness.ok`
branch (`saffron/cli.py:714`). `run_batch`, whose own comment says it "is what
makes the batch row close `INFRASTRUCTURE` and exist at all", is not reached
until line 735. A `SpecError` from discovery therefore reaches the catch-all in
`main`, which wraps every subcommand, prints one line, and returns `2`. The exit
code is correct. There is still no batch row, no task row, and nothing in
`~/.saffron/ledger.db` to say that a night began.

## Problem

The night's stdout is its only human-readable account, and under launchd
without `PYTHONUNBUFFERED=1` a SIGTERM discards it (item **46**, `CLAUDE.md`).
So the failure `SA-0065` was written to make visible is visible on a terminal
nobody is watching and invisible everywhere the morning looks. §6's morning
queue reads `batches`. A night with no row is not a failed night there. It is
no night at all.

The state already exists. `run_batch` closes a batch `INFRASTRUCTURE` when
readiness fails, and closes one in its `finally` when anything below it raises.
The fix is about reaching that close, not inventing a new one.

## Out of scope

**`KeyboardInterrupt` and other `BaseException`s during resolution.** A Ctrl-C
before the loop starts is an operator who is present, and `run_batch`'s own
`finally` already covers one after the row exists. Catch `Exception`, the same
width `run_batch` uses for a runner that raises.

**What `discover_specs` refuses.** That is `SA-0065`'s, and `saffron/intake.py`
is forbidden here.

**A new stop reason.** A night that cannot resolve its queue never started a
task. `INFRASTRUCTURE` is the stop a failed readiness check already writes
(`batch.py:137-143`), and it is the only stop reason that says the machine
rather than the work was wrong.

**`saffron queue`.** The attended preview has no night to record, and exiting 2
there through `main`'s catch-all is correct.

## Notes for the agent

**This spec creates new code, so its new criteria carry witnesses and no
mutants.** A guard that does not exist yet has no spelling to pin. The last two
criteria name tests that already exist and must keep passing unchanged.

**Every new witness must fail with `cli.py` and `batch.py` reverted, not merely
be missing at base.** The `revert` gate re-runs each new witness against the
reverted source and blocks any that still pass. Each of the three new tests
therefore has to observe something only this change produces: the row, or the
`batch:` line. Import what the tests need inside the test, not at module scope.
A module-scope import of a name you add makes the reverted run a collection
error, which `revert` reads as `skip`, and then it checks nothing.

**Two shapes will pass the first two criteria, and only one passes the third.**
The nearest shape is handing `run_batch` a failed `Readiness` whose `step` names
the queue. It closes the row with no change to `batch.py`, but the existing
print path then reports `readiness failed at …`, which is false. Either make
the `batch:` line distinguish the two causes, or give `run_batch` a way to
learn that resolution failed. `batch.py` is in `touches` so the second shape is
available. Take whichever is smaller once the third criterion is met.

**Assert the row through the ledger, not through a mock of `run_batch`.** The
defect is a missing row, and a test that replaces `run_batch` with a lambda
cannot see one. `main(["--home", …])` creates a real `ledger.db`, and
`test_an_unready_night_still_leaves_a_row_saying_it_was_attempted` already reads
`batches` that way. To make resolution raise, monkeypatch `cli._resolve_queue`
to raise `intake.SpecError`. Building a git fixture without `.saffron/specs/` is
also acceptable, but it is not needed.

**Two strings assume readiness is the only failure before the loop.** Update
`_batch`'s docstring, which still says `saffron/batch.py` is forbidden and that a
readiness failure is the only `INFRASTRUCTURE` whose cause is read back, and
`_no_candidate_should_run`'s message.
