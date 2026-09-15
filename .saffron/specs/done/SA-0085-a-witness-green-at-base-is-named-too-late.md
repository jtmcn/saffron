---
id: SA-0085
title: a witness already green at base is named only after the attempts it cannot pass have been paid for
type: bug
priority: 3
depends_on: [SA-0084]
touches:
  - saffron/gates/core/criteria.py
  - saffron/cell/session.py
  - saffron/events.py
  - tests/test_criteria.py
  - tests/test_session.py
  - tests/test_events.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - spikes/**
  - tests/fixtures/**
  - saffron/gates/suite.py
  - saffron/gates/runner.py
  - saffron/gates/contract.py
  - saffron/gates/baseline.py
  - saffron/phases/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/watch.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/intake.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 50
acceptance:
  - claim: >-
      When the baseline suite shows a witness already passing at `base_sha`,
      and its criterion does not declare `preserves`, the task names that
      witness before the first agent turn. Today nothing names it until
      `criteria` fails the first attempt with `witness-green-at-base`, which no
      repair turn can fix, so the task pays for attempts to learn what its
      baseline already knew.
    witness: tests/test_session.py::test_a_witness_green_at_base_is_named_before_the_first_turn
  - claim: >-
      The naming travels on the baseline's own event and is rendered by
      `describe`, so it reaches `events.jsonl` and `saffron watch`, not only
      the attended terminal.
    witness: tests/test_events.py::test_a_baseline_naming_a_green_witness_renders_it
  - claim: >-
      `criteria` still fails such a witness at head, as it does today.
    witness: tests/test_criteria.py::test_a_witness_green_at_base_fails
    preserves: true
  - claim: >-
      Every line family still renders from its kind, as it does today.
    witness: tests/test_events.py::test_every_family_has_a_kind_and_renders
    preserves: true
---

## Context

`docs/BACKLOG.md` item **23**, found reviewing `SA-0011`. `criteria` reports
`witness-green-at-base` for a criterion that does not declare `preserves` and
whose witness already passed at `base_sha`. That failure blocks, and no repair
turn can fix it: the agent's only routes are renaming or deleting a test that
already exists, and `census` and `integrity` block both. So an authoring
mistake, a witness that already passes, costs attempts until the no-progress
rule ends the task.

It cannot be caught at intake, because it needs the suite. The baseline suite
already has the answer before any turn runs: `criteria` itself skips at
baseline (`saffron/gates/suite.py`), but the baseline's results hold the
witness's name among the collected tests and outside the failures.

The item asked for a `watch()` line. `watch()` is gone: every line the
supervisor prints is now an `Event` that `describe` renders (`SA-0030`).

## Problem

An operator learns that a spec cannot pass as written only after paying for
the attempts that prove it, on the unattended night where nobody reads the
first one.

## Out of scope

**Ending the task early.** A task stopped for this reason needs a terminal
state for it. That is vocabulary (`ontology/factory.ttl`), done by hand. This
spec names the witness and changes nothing about how the task proceeds.

**Intake.** Intake never runs the suite.

## Notes for the agent

**The rule already exists, in `criteria`.** It is `_judge`'s last branch, built
on `_side` and `_green`. Expose it from `saffron/gates/core/criteria.py` as one
function both callers use, rather than restating it in `session.py`. Two copies
of one rule is how they drift.

**It says nothing where `criteria` would say nothing.** No witness is named for
a `preserves` criterion, for a witness absent at base, or when the baseline's
enumeration is unreadable (no gate reported what it collected, or its failures
are not keyed on node ids). Assert those cases inside the first witness. As
separate criteria they would pass with the source reverted, and `revert` would
block them.

**Carry it on `Baseline`, as a defaulted field.** A log written before this
change has no such field, and `read_log` must keep reading it. `describe`
renders the names as a further line after the ones it already renders. A new
line shape needs a `FAMILIES` row, and `tests/test_events.py` pins the count.

**Emit it where the baseline is emitted in `_drive_cell`,** before the first
agent turn. `_drive` in `tests/test_session.py` takes injected suites and a
`capture` list of the raw events. Other tests there stub the baseline suite's
results this way.

**This is new code, so the criteria carry witnesses and no mutants.** Every new
witness must fail with the source reverted. Import nothing new at module scope,
because a module-scope import of a name you add turns the reverted run into a
collection error, which `revert` reads as `skip`.

**This spec is cut from `SA-0084`'s branch**, which edits `describe` in the same
file.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
