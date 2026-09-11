---
id: SA-0067
title: a task left in flight leaves the night reporting DRAINED and exiting 0
type: bug
priority: 1
depends_on:
  - SA-0066
touches:
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_batch.py
  - tests/test_cli.py
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
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/replay.py
  - tests/ontology/**
budget_usd: 6
max_attempts: 3
max_turns: 50
risk: standard
acceptance:
  - claim: >-
      A night whose queue drains after a task came back still in flight closes
      `INCOMPLETE`, not `DRAINED`. `DRAINED` says the queue emptied, and a queue
      that emptied with a task stopped mid-phase is a different night: nobody
      can say what happened to that task, which is not the same as the task
      failing.
    witness: tests/test_batch.py::test_a_task_left_in_flight_is_not_a_clean_drain
  - claim: >-
      `INCOMPLETE` outranks the other ordinary stop reasons. A night that left
      a task in flight and then stopped at `BUDGET` or at `UNTIL` still closes
      `INCOMPLETE`, because what the morning most needs to know is that a task
      reached no end state, not which of the ordinary limits came first. The
      witness drives both a `BUDGET` stop and an `UNTIL` stop after an in-flight
      task.
    witness: tests/test_batch.py::test_a_task_left_in_flight_outranks_an_ordinary_stop
  - claim: >-
      `INFRASTRUCTURE` outranks `INCOMPLETE`. A breaker that fires after a task
      was left in flight still closes `INFRASTRUCTURE`, the one stop reason that
      must never be hidden behind another, and the night still names the task
      it left in flight, and that task's state, on the way out.
    witness: tests/test_batch.py::test_the_breaker_still_reports_infrastructure_over_a_task_left_in_flight
  - claim: >-
      The breaker is unchanged: an in-flight outcome still resets the
      consecutive-abort count, so two provider blips in a row do not end a night
      that would have recovered on its third task. A night of `GATE_ERROR`,
      `REBUTTING`, `RATE_LIMITED`, `READY_FOR_REVIEW` runs all four candidates
      and closes `INCOMPLETE`, not `INFRASTRUCTURE`. Item 70 argues this
      deliberately, and the recovery it relies on works: the next batch scan
      stamps the corpse `ORPHANED` and requeues it.
    witness: tests/test_batch.py::test_in_flight_outcomes_do_not_fire_the_breaker
  - claim: >-
      The night names each task it left in flight, and the state it stopped in,
      on the way out, whatever the stop reason, `INFRASTRUCTURE` included. A
      stop reason says that something went wrong. The line says which spec to
      look at.
    witness: tests/test_batch.py::test_a_task_left_in_flight_is_named_on_the_way_out
  - claim: >-
      `saffron batch` exits 2 for an `INCOMPLETE` night and prints
      `batch: INCOMPLETE`, not the infrastructure line. `0` means the night made
      it, and this one did not, but the machine did not break either, and a
      line saying it did sends the operator to the wrong place. It still never
      exits `1`, which is reserved for a task's own failure (§4.2.1).
    witness: tests/test_cli.py::test_a_night_that_left_a_task_in_flight_exits_two
  - claim: >-
      `DRAINED`, `BUDGET` and `UNTIL` still exit 0 when no task was left in
      flight.
    witness: tests/test_cli.py::test_the_three_ordinary_stop_reasons_all_exit_zero
    preserves: true
  - claim: >-
      An `EXHAUSTED` task between two aborts still resets the breaker. A task
      that failed its gates earned its outcome, and that is not what this spec
      changes.
    witness: tests/test_batch.py::test_an_exhausted_task_between_two_aborts_resets_the_breaker
    preserves: true
---

## Context

`docs/BACKLOG.md` item **70**, measured 2026-09-06 driving `SA-0057`
(`docs/evidence/2026-09-06-a-provider-error-inside-a-night.md`). The provider
erred during REBUT, the agent exited 1 with no output, and `run_one_cell`
returned an outcome in state `REBUTTING`:

```
agent: API Error: Server error mid-response. The response above may be incomplete.
REBUT: the rebuttal moved no commit and made no argument
SA-0057    REBUTTING
batch: DRAINED
```

Exit `0`, $3.75 spent, no pull request, and a night an unattended caller
records as clean. `batch.ABORT_STATES` does not contain `REBUTTING`, so the
loop treated it as a state the task earned and drained.

**The vocabulary this spec implements against was added by hand before it was
queued.** `INCOMPLETE` is a member of `factory:BatchStopReason`, `CONTEXT.md`
defines it, §4.2.1 maps it to exit 2, `batch.StopReason` lists it, and the
`CHECK` on `batches.status` admits it, with a migration for existing ledgers.
`tests/ontology/test_vocabulary_agrees_with_code.py` holds the vocabulary, the
`Literal` and the `CHECK` equal, so they could only move together, alongside
`CONTEXT.md` and §4.2.1, which are `protected`. At this spec's base the value
exists and nothing returns it. That is the whole of what is left.

**If `batch.StopReason` at your base has four members, stop.** The by-hand half
did not land, so this spec cannot be satisfied without editing forbidden
files. Record that in your notes rather than working around it.

## Problem

§4.2.1 is right that a night that drains with three failed tasks did its job,
since individual outcomes are the morning queue's business. But a task in
flight has no outcome. `REBUTTING` is not a failure the morning can read. It is
the absence of an answer, and the loop cannot tell that apart from a task that
finished.

"In flight" is already defined: `reconcile.IN_FLIGHT_STATES`, the set the next
batch scan reads to decide that a row is a corpse. Read that set. Do not copy
it. A second list is how the loop and the scan come to disagree about what a
finished task is. No witness can tell a copy from the original, so a reviewer
will check this by eye.

## Out of scope

**The breaker's set.** `ABORT_STATES` stays as it is. Adding in-flight states
to it is the nearest edit to hand, and item 70 explicitly argues against it.
The fourth criterion pins that decision.

**Retrying inside the night.** The scan is resolved once, before the loop, and
that is what makes termination structural. A retry reintroduces the "does the
queue change" question the `for` loop was written to avoid.

**The vocabulary, `CONTEXT.md`, §4.2.1, the ledger `CHECK` and its
migration.** All landed by hand. `saffron/ledger.py` and `tests/ontology/**`
are forbidden here for that reason.

**A runner that raises.** That already counts as an abort. Leave it.

## Notes for the agent

**This spec creates new code, so its new criteria carry witnesses and no
mutants.** The last two criteria name tests that already exist.

**Every new witness must fail with `batch.py` and `cli.py` reverted, not merely
be missing at base.** The `revert` gate re-runs each new witness against the
reverted source and blocks any that still pass. Criteria 3 and 4 each describe
something that is already true at base: a breaker firing after an in-flight
task already reports `INFRASTRUCTURE`, and an in-flight outcome already resets
the count. Each of their witnesses must also assert what this change adds: the
named task on criterion 3, and the `INCOMPLETE` close on criterion 4. Import
new names inside tests, not at module scope. A module-scope import of a name
you add makes the reverted run a collection error, which `revert` reads as
`skip`.

**Closing the row is one call, and it must happen once.** Every `return` in
`_drive` is paired with a `close_batch`, and the `finally` in `run_batch`
closes the row only when nothing below returned. Keep that shape: decide the
reason, close once, return it. Closing `BUDGET` and then trying to amend the
row to `INCOMPLETE` is two writes where one decision belongs.

**`SA-0066` changes the same end of `_batch`.** This spec is stacked on it, so
its `batch:` line for an unresolvable queue, and any parameter it added to
`run_batch`, are already in your base. Keep both. Decide the `INCOMPLETE` line
before the readiness and resolution lines are chosen, so a night that left a
task in flight never prints either of those.

**The docstrings that count four reasons are yours to update.** `batch.py`'s
module docstring ("stopping four ways"), `run_batch`'s return description, the
comment above `StopReason`, `cli._batch`'s docstring, and the comments in
`tests/test_batch.py` and `tests/test_cli.py` that walk "all four stop reasons"
all become false when the loop returns a fifth.

**`SA-0069` also edits `tests/test_cli.py`.** If both pull requests are open at
once, expect to rebase one of them. The batch scan's overlap refusal holds the
second back if the first is already open when the night is scanned.
