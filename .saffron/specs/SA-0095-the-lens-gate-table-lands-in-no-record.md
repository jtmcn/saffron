---
id: SA-0095
title: the gate suite the lenses are shown is the one judged suite that lands in no record, so nothing afterwards can tell an honest table from a forged one
type: bug
priority: 2
depends_on: [SA-0094]
touches:
  - saffron/cell/session.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 16
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      The gate suite REVIEW's lenses are shown is written to the task
      directory, beside the pre-turn baseline the task already writes there, in
      the same shape — every result the suite produced, as JSON. Today it is
      rendered into a lens prompt and discarded, and no file, event or ledger
      row carries it.
    witness: tests/test_session.py::test_the_gate_table_the_lenses_were_shown_lands_beside_the_baseline
  - claim: >-
      That file is written before the first lens turn, so a task whose REVIEW
      ends in the middle still carries the table its lenses had been shown.
    witness: tests/test_session.py::test_the_lens_gate_table_is_written_before_the_first_lens_runs
  - claim: >-
      The lenses are still shown a gate table computed outside the
      implementer's cell.
    witness: tests/test_session.py::test_the_lenses_are_shown_a_gate_table_computed_outside_the_implementers_cell
    preserves: true
  - claim: >-
      A gate that errors in the gate cell is still not the task's failure.
    witness: tests/test_session.py::test_a_gate_that_errors_in_the_lens_gate_cell_is_not_the_tasks_failure
    preserves: true
  - claim: >-
      A green run still prints exactly the lines the golden watch fixture
      carries.
    witness: tests/test_events.py::test_watch_output_matches_the_golden_fixture
    preserves: true
---

## Context

Backlog item **141**, found reviewing `SA-0089` (PR #282).

Every other judged gate suite in a task lands somewhere. `_judge` writes each
implementer suite with `ledger.record_gate_result`. The pre-turn baseline is
written to `task_dir/baseline.json` *and* recorded row by row. `repair_loop`
and `_rebut_gates` each emit an attempt event. The gate cell's comparison —
the one `SA-0089` built so the lenses would stop reading a table the
implementer's own container computed — is emitted nowhere, recorded nowhere
and written to no file. It is rendered into a lens prompt and dropped.

`CONTEXT.md` says a gate suite's number counts the gate suites judged in a
task, and `DESIGN.md` §5.4 has a gate result belonging to an attempt. Both
assume a judged suite lands somewhere. This one does not, so **nothing in the
ledger or the task directory distinguishes a run whose lenses saw an honest
gate table from one where they saw a forged one** — which is the exact property
`SA-0089` exists to establish. The spec establishes it and keeps no evidence
that it held.

## Problem

The one gate suite whose whole purpose is to be trustworthy is the one nothing
afterwards can read.

## Out of scope

**Recording the gate cell's results in the ledger with
`ledger.record_gate_result`.** Item 141 offers the file or the ledger row; this
spec takes the file, beside `baseline.json`, because it is the shape a reader
already knows and because these results belong to no attempt — REVIEW is not an
implementer attempt, and §5.4's rule is that a gate result belongs to one.
Changing what an attempt is, is a larger question than this spec.

**The implementer's own suites, the baseline, and what either writes.**
Unchanged. This adds one file; it removes nothing and rewrites nothing.

**What the lenses are shown.** The prompt keeps carrying exactly the summary
it carries today. This spec writes down what was shown, and does not change it.

**The report and the pull request body.** Whether a reader ever sees this file
rendered is a later question. Writing it is what unblocks that; rendering it is
not this change.

## Notes for the agent

**Criteria 1 and 2 carry witnesses and no mutants.** The write is new code, so
no text exists at base that a mutant could pin honestly, and `witness` will
report `skip` for both. Criteria 3–5 are `preserves` and name tests that exist
at base — `git grep` them. Criterion 5's test and its fixture are both outside
`touches`, which is deliberate: it is the assertion that this change printed
nothing.

**Follow `baseline.json`'s own write, a few hundred lines up the same file.**
It is `json.dumps([r.model_dump() for r in baseline.results], indent=2)` into
`task_dir`. Match it: the same serialisation, the same indent, a sibling name.
A reader comparing the two files should not have to learn a second format.

**`task_dir` has to reach the function that runs the gate suite, and today it
does not.** The call site in `_drive_cell` has it in scope. Pass it as an
argument rather than recomputing it — `_drive_cell` builds `task_dir` once so
that everything downstream agrees on the object it is being handed, and the
comment at its definition says so.

**Write the file before the lenses start, not after they finish.** That is
criterion 2 and it is the whole value of the record: a REVIEW that ends on a
wall, a budget stop or an exception still leaves the table its lenses were
shown. `tests/test_session.py` already has tests that stop the lenses partway
— `test_a_wall_after_the_gates_go_green_stops_the_lenses` is one — and
`_stub_the_runtime` records a shared `cell.order` timeline that makes "before
the first lens turn" assertable rather than merely "both happened".

**Criterion 1's witness must read the file's contents, not its existence.**
A test that asserts the path exists passes over a file containing `[]`, and an
empty table is precisely the failure mode a forged toolchain would produce.
Make the stubbed gate cell suite report something the implementer's suite does
not — `_stub_the_runtime` already takes a `gate_cell_suite` argument for
exactly this, added by `SA-0089` — and assert the file carries *that*.

**Both new witnesses must fail with `session.py` reverted.** Reverted, no such
file is written at all, so an honest test of either fails. Import nothing new
at module scope: a module-scope import of a name you add turns the reverted run
into a collection error, which `revert` reads as `skip` and the anti-theater
gate then checks nothing. This was missed in five of eight specs in the
`SA-0066`–`SA-0073` review, so check it explicitly before you finish.

**The file is a control artifact, so write it from the value in hand.**
Extract and write it at the moment the suite returns, never by re-reading
anything out of `/work`. A file left in a cell's workspace is a claim, not a
record, and this file exists to be the record.

**`EventLog.append` never raises, and neither should this write take the task
down.** But do not swallow the failure silently either: the task directory is
the host's own, a failure to write there is infrastructure, and `_drive_cell`
already has the shape for reporting one. Follow what the `baseline.json` write
does — it does not guard, because a task directory that cannot be written to
has already failed the task — rather than inventing a third policy.

**Print nothing new on the green path.** Criterion 5 is the check.
`_rebut_gates`' callers emit an attempt event for every suite; this write emits
none.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**This spec builds on `SA-0093` and `SA-0094`.** By your base the gate cell's
lifecycle is `critic_cell`'s, entered with a network of its own. Read the code
as it is at your base, not as item 141 describes it.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included, and this change is well inside that.
