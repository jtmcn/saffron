---
id: SA-0099
title: runs.preflight is declared on every run and written on none, so the batch header's per-repo preflight field has no source
type: bug
priority: 2
depends_on:
  - SA-0094
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - tests/test_ledger.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/preflight.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/events.py
budget_usd: 16
max_turns: 90
acceptance:
  - claim: >-
      A run whose baseline suite aborted records a preflight outcome saying the
      machine was not fit to start, and a run that reached the implementer
      records one saying it was fit. The two values differ, and each names its
      own case. Today the column is NULL on both.
    witness: tests/test_session.py::test_a_run_records_whether_its_preflight_passed
  - claim: >-
      A run that unwinds through the abort path after its baseline suite
      already passed records a preflight outcome saying preflight passed. The
      abort is recorded as the run's status and never as a preflight failure,
      because an interrupt during REVIEW says nothing about whether the
      machine was fit an hour earlier.
    witness: tests/test_session.py::test_an_abort_after_a_passing_preflight_is_not_a_preflight_failure
  - claim: >-
      The recorded outcome is one of a closed set. Asking the ledger to store a
      value outside that set raises, and the row keeps the value it had rather
      than carrying an invented word. This holds on a ledger built by the
      previous schema as well as on a fresh one, because the ledger this defect
      is measured on already has its runs table.
    witness: tests/test_ledger.py::test_a_preflight_outcome_outside_the_closed_set_is_refused
  - claim: >-
      A ledger written by the previous schema still opens and still accepts a
      write, with its existing runs left as they are. No run that nobody
      observed gains an outcome by backfill.
    witness: tests/test_ledger.py::test_a_ledger_built_by_the_previous_schema_still_opens_and_writes
    preserves: true
---

## Context

This spec is Task 4 of
`docs/superpowers/plans/2026-08-31-operator-visibility.md`, which specified it
as `SA-0032`. Parts 2 and 3 of that plan were never built.
`.saffron/specs/done/` runs `SA-0031` and then `SA-0040`, so `SA-0032` through
`SA-0039` do not exist. This spec is filed at the highest current id plus one,
per `docs/agents/issue-tracker.md`.

`DESIGN.md` §4.1 gives `runs` a `preflight` column. `saffron/ledger.py:52`
declares it as `preflight  TEXT,`. §6 lists per-repo preflight status among the
batch header's six fields, and calls this one a column that exists and is never
written.

Measured 2026-09-17 against `~/.saffron/ledger.db`: 0 of 99 runs carry a
non-NULL `preflight`. The column has no writer. The word occurs twice in
`saffron/ledger.py`, at `:52` in the schema and at `:318` inside a comment
about a different subject.

The write was never wired, rather than never designed.
`saffron/cell/session.py:1331` mints the row with
`run_id = ledger.create_run(repo_id, spec.base_sha)`. `create_run` at
`saffron/ledger.py:404-418` inserts `repo_id`, `base_sha`, `batch_id` and a
literal `'RUNNING'` status. That is four columns, not five. `finish_run` at
`saffron/ledger.py:420` takes a `run_id` and a `status`, and nothing else.

The outcome is known in two places, and discarded at both.

- `saffron/cell/session.py:1256-1261` defines `_preflight`, which emits a
  `Preflight` event per step. `cell_up` receives it as `note=_preflight` at
  `saffron/cell/session.py:1363-1376`. Every step's outcome reaches the event
  log and the terminal. None of it reaches a column.
- `saffron/cell/session.py:1408-1418` decides the machine was unfit. The branch
  `if baseline.aborted:` sets the task to `PREFLIGHT_FAILED`, then closes the
  run `COMPLETE`. The task state carries that fact. The run row does not.

`runs.status` is no substitute, and the code says so itself.
`saffron/cell/session.py:2317-2327` is the abort path. Its comment calls a
preflight that raises "the path an operator hits first", and closes such a run
"ABORTED, not COMPLETE". So `ABORTED` already carries a preflight that raised,
folded together with Ctrl-C and with every other `BaseException` from anywhere
in a long task.

Measured the same day, `runs.status` reads `COMPLETE` on 94 rows and `ABORTED`
on 5. Which of those five was a machine that would not start is not
recoverable from the column.

`tests/test_ledger.py:797` is the guard against this defect. Its docstring
calls the shape a column written at scan and read by nobody. It asserts over
`batches` and `tasks` only, and reaches no column of `runs`. That is why this
defect survived.

**Which of §6's six header fields this column is.** State it once, so a later
spec does not guess. §6 lists per-repo preflight status and base-suite status as
two fields, and §4.1 gives a run "its own preflight outcome, and its own
baseline". They are different things. This column is the preflight one. Criterion
1 sources it from the baseline suite anyway, because a readiness failure happens
before `create_run` and reaches no run row at all. `DESIGN.md:267-268`
already reads `PREFLIGHT_FAILED ◀── the baseline suite errored`, which is the
same reading. Say so in the pull request body, so the header spec does not render
a base-suite fact under a preflight label.

## Problem

- **The column exists and nothing assigns it.** This is a write that was never
  wired, not a missing schema.
- **A failed preflight is the most expensive kind of nothing.** It is charged
  to nobody. Whether the machine was fit survives only in the terminal scroll,
  and in a `PREFLIGHT_FAILED` task state one join away.
- **`ABORTED` conflates a machine that would not start with an operator's
  Ctrl-C.** Five rows carry it. The column that would separate them is NULL.
- **§6 states the argument itself.** A header field with no source is not a
  smaller header. It is a field that renders a confident em-dash.

## Out of scope

**Rendering it.** `saffron/report/**` is forbidden. The batch header belongs to
a later spec. A written column with no reader beats a reader inventing one.

**The other five header fields.** The diff stat and the trailing accept rate
have no source yet, and each is its own question. Wall clock has one already, in
`batches.started_at` and `batches.ended_at` at `saffron/ledger.py:38-39`. Do not
widen this spec to any of them.

**Changing what preflight checks.** `saffron/preflight.py` is forbidden. This
spec records an outcome. It does not alter one, and it adds no step.

**Backfilling the 99 existing rows.** Those rows stay NULL. A value invented
for a run nobody observed is the failure §4.1 warns about. It is a column named
for a measurement it cannot make.

**The gate set preflight parses and drops.** `ontology/RATIONALE.md`'s Q3 is
blocked on it. It is the same shape as this defect, in the same region of the
same file. Preflight computes something and discards it. It is a different
value. Taking it is an unasked-for fix riding inside a bug fix. Name it in the
pull request body, and do not fix it.

**The vocabulary entry for the closed set.** `ontology/` and `CONTEXT.md` are
both forbidden. The second is generated from the first, so a cell cannot move them
together. The follow-up is filed by hand as item 169 with this spec.

**A tenth event kind, or a new table.** `saffron/events.py` is forbidden.
`Preflight` already exists as a kind, and already carries every step. This spec
adds a column's writer, not a vocabulary.

## Notes for the agent

**This spec's change is new code.** Three criteria declare a witness and no
mutant. No existing text pins honestly, because the write does not exist. The
spelling of the method and of the stored values is yours. Expect `witness` to
report `skip` for those three. The fourth criterion is `preserves` over
`tests/test_ledger.py:717`, a test that exists today and must keep passing.

**The outcome is an enumeration, not a free string.** `events.Budget`'s
docstring in `saffron/events.py` states the principle for the ceiling that
stopped a task: a typed field over an enumeration, never a free string.
`batches.status` carries a closed set of that kind, tested by
`tests/test_ledger.py:635`. Take the set, and read the next paragraph before
taking its `CHECK`. Add no free-text reason column. A bounded reason string was
this spec's sketch in the plan, and it is the weaker answer. It invites the
terminal's prose into a column an operator wants to `GROUP BY`.

**A `CHECK` in `SCHEMA` alone protects no ledger that already exists.** That
includes the only ledger this defect is measured on. `saffron/ledger.py:47`
declares `CREATE TABLE IF NOT EXISTS runs`, and `_widen_batch_status` at
`saffron/ledger.py:222-226` states the consequence in its own words. A
`CREATE TABLE IF NOT EXISTS` "leaves an existing table's CHECK as it was", so a
ledger from before `INCOMPLETE` refused the first night to end that way. So a
`CHECK`
added to `SCHEMA` passes a witness built on a fresh `tmp_path` database. The
99-run ledger keeps accepting any invented word. Put the refusal in the Python
write, where it holds on every ledger. A `CHECK` for fresh ledgers is welcome
beside it, and is not the refusal criterion 3 asks for. Retrofitting one is the
12-step rebuild `_widen_batch_status` performs, and `tasks.run_id` and
`gate_results.run_id` both reference `runs`, so it costs more than it buys here.

**Criterion 3 drives two ledgers in one plain test.** A fresh one, and one built
by the previous schema. `tests/test_ledger.py:273` and `:1137` both open an older
database already, so copy whichever shape fits. Keep it one `def` rather than a
parametrised test, because `criteria` matches a bare node id by exact string.

**Two values are the floor, not the target.** A passed value and a failed value
satisfy criterion 1. A run that never reached the baseline suite is a different
fact from one whose suite ran and aborted.
`saffron/cell/session.py:2317` is reachable before
`saffron/cell/session.py:1408` runs. Decide whether that third case earns a
third value. Whichever set you choose, write it down in one place, and make the
`CHECK` agree with that place by construction. Two lists an editor must change
together is how the fifth instance of item 18 happened.

**Criterion 1's plausible wrong implementation is one value for both cases.**
It answers nothing. A write recording that preflight ran on every run satisfies
non-NULL on every run. The witness must assert that the two runs' values differ,
and that each is the one its own case calls for.

**Criterion 2's plausible wrong implementation is a failure on every `ABORTED`
run.** It is wrong. That is the easy read of the abort path.
`saffron/cell/session.py:2317` catches `BaseException` from anywhere in the
body, REVIEW and PACKAGE included. Drive an abort that lands after the baseline
suite passed, and assert that preflight still reads as passed.

**Write it where the outcome is known.** Do not re-derive it from a task state.
Deriving `runs.preflight` from `tasks.state == "PREFLIGHT_FAILED"` passes
criterion 1. It is the same defect wearing a different hat. The run row would
report a join rather than an observation. A run with two tasks has no single
answer.

**`runs.preflight` is per-run, and a run is one repo's slice of a batch.** A
batch is not a run, per §4.1 and `CONTEXT.md` §8. Resist recording this at
batch level, which has no column for it.

**Do not fold it into `runs.status`.** `status` says how the run ended.
`preflight` says whether the machine was fit to start. A run passes preflight
and still aborts, which is criterion 2.

**`tests/test_session.py` is large and shared.** Two queued specs also name it,
`SA-0093` and `SA-0094`. Keep the diff to the two new tests, plus whatever one
existing stub needs to reach the new write. `census` compares test names, so
rename nothing.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
