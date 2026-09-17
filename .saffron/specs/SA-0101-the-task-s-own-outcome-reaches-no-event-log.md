---
id: SA-0101
title: the task's own terminal announcement is a bare print, so its event log ends before the outcome and emit is not the whole seam
type: bug
priority: 2
depends_on:
  - SA-0099
  - SA-0098
touches:
  - saffron/events.py
  - saffron/cell/session.py
  - tests/test_events.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/watch.py
budget_usd: 14
max_turns: 90
acceptance:
  - claim: >-
      A caller that supplies its own emit receives the task's terminal
      announcement through it, and process stdout carries no copy of that line.
      Today the line is a direct print, so a caller supplying emit gets a line
      it cannot redirect.
    witness: tests/test_session.py::test_the_terminal_announcement_reaches_emit_and_not_stdout
  - claim: >-
      The rate-limit rejection behaves the same way through the RateLimited
      path. It reaches the caller's emit, it names the reopening time when one
      is known, and process stdout carries no copy of it.
    witness: tests/test_session.py::test_the_rate_limit_rejection_reaches_emit_and_not_stdout
  - claim: >-
      The outcome the task ended on reaches events.jsonl, so reading the log
      back and describing it reproduces the same line the print wrote, with the
      same state, the same spend and the same session id. Today the log's last
      event is PACKAGE's, and the outcome appears nowhere in it.
    witness: tests/test_events.py::test_the_outcome_event_round_trips_and_describes_as_its_old_line
  - claim: >-
      Every kind still round-trips through the log and still has its wire keys
      pinned, the new one included.
    witness: tests/test_events.py::test_every_kind_is_round_tripped_and_its_wire_keys_pinned
    preserves: true
---

## Context

Backlog item **43**, filed as `partial` and left half open by `SA-0030`.

`saffron/events.py` says what the module is for. Its docstring counts 64 call
sites that "author prose straight into `watch()`, and the structure behind each
line dies with the terminal scroll". Ten frozen kinds and a durable log are the
fix. `FINDINGS` in that file is the honest record of what would not fit, and
its first entry is this defect.

Two lines never became events. Both are in `_drive_cell`.

- `saffron/cell/session.py:2271` prints the task's terminal announcement:
  `f"{outcome}: ${spent:.2f} spent, session {session_id}"`. Its comment at
  `:2265-2270` gives the reason. A `Terminal` is scoped to the five zero-commit
  IMPLEMENT endings, and a `Budget` carries a ceiling, a value and a limit.
  Neither fits an arbitrary outcome word with a session id.
- `saffron/cell/session.py:2293-2300`, inside `except RateLimited`, prints
  `rate limit: rejected` and the reopening time. Its comment at `:2291-2292`
  says it shares the exemption above.

Two consequences, and the second was not disclosed until a review found it.

**The event log ends before the outcome.** Measured 2026-09-17 against
`~/.saffron/batches/v0/SA-0095/events.jsonl`: the last event is PACKAGE's, and
no line in the file names `READY_FOR_REVIEW`, the spend or the session id.
`saffron watch` renders the log through `describe`, so it shows a task's whole
run and never how it ended. Across the 54 event logs on that host, `Terminal`
appears twice and no kind carries an outcome.

**`emit` is not the supervisor's whole output seam.** Both lines go to process
stdout whatever the caller passed. So a caller supplying its own `emit` still
gets two lines it cannot redirect, and the one it most wants is the outcome.
The test harness hides this: `tests/test_session.py:1072` patches
`session.print` with `raising=False`, so the leak is invisible unless a test
opts out through the `use_default_emit` seam its fixture documents at `:984`.

**Two comments about the same decision disagree, and one is stale.**
`saffron/cell/session.py:2268` calls the missing kind "a tenth kind".
`events.FINDINGS[0]` calls it "a eleventh kind". `Event` in
`saffron/events.py` unions ten kinds, and `_KINDS` maps ten names. So eleventh
is right, and the `session.py` comment counts from a draft that had nine.

## Problem

- **A task's log cannot answer how the task ended.** That is the first question
  anyone reads a log to answer.
- **`saffron watch` shows everything except the outcome.** It follows the log
  and adds no second source, so a finished task ends mid-PACKAGE on screen.
- **A caller cannot capture the supervisor's whole output.** Two lines bypass
  `emit`, which is the seam every other line goes through.
- **The gap is worst where nobody is watching.** Under `saffron batch` the
  terminal scroll is the night's record, and `CLAUDE.md` notes SIGTERM discards
  it. The durable log is what survives, and it omits the outcome.

## Out of scope

**The `re-verify` line.** `events.FINDINGS[1]` names it and
`saffron/phases/package.py` is forbidden. Its problem is a `LineLabel` casing
rule, not a missing kind, and it stays item 43's.

**The `stacked on` line.** `saffron/task.py:287-291` prints it under a
`ponytail:` comment citing item 43, and `saffron/task.py` is forbidden. No kind
carries `CellSpec.stacked_on` at all, which is a wider change than this one.

**Item 43's close.** Two of its four lines stay after this spec, so the item
stays `partial`. Do not mark it done.

**`saffron/watch.py`.** It renders through `describe` already and needs no
change to show a kind that exists. It is forbidden, and a new filter for the
new kind would be the wrong answer.

**Widening `Terminal`.** Its five reasons are the zero-commit IMPLEMENT endings
and backlog item 37 already disputes its name against `CONTEXT.md`. Adding an
outcome word to it makes that worse.

**The vocabulary entry.** A new kind is a new term, and `CONTEXT.md` is
generated from `ontology/factory.ttl`, so a cell cannot move both halves. The
follow-up record is filed by hand with this spec.

## Notes for the agent

**This spec's change is mostly new code.** Three criteria declare a witness and
no mutant. The kind does not exist, so its field spellings are yours.
Expect `witness` to report `skip` for those three. The fourth is `preserves`
over `tests/test_events.py:1143`, a plain test function that must keep passing
once the new kind joins whatever list it walks.

**One kind covers both lines, and that is the design.** Both are the task's own
terminal announcement. The rate-limit rejection is the outcome `RATE_LIMITED`
plus a reopening time, so a single kind with an optional reopening field carries
both. Two kinds for one fact is the shape `events.py` exists to refuse.

**`RATE_LIMITED` is not `EXHAUSTED`.** A provider ceiling and a task that could
not pass its gates are different outcomes and say different things. Whatever
field carries the state must keep them apart, and the rendered line for each
must stay distinguishable.

**Criterion 1's wrong implementation is an event beside the print.** The seam
stays broken. Adding the emit and leaving the print still satisfies "the caller
receives it". So the witness must assert the line is absent from stdout. Drive it
through the fixture's `use_default_emit` path, rather than the `session.print`
double at `tests/test_session.py:1072`. A witness that keeps that double cannot
observe this at all.

**Criterion 3's wrong implementation is a kind that renders differently.** An
operator learned the old line. `saffron watch` also replays old logs beside new
ones. Read the format string at `saffron/cell/session.py:2271`. Make `describe`
reproduce it exactly, the two-decimal spend included. Assert against the whole
text, never a substring.

**`spent` is read back from the ledger on the rate-limit path, and that is
deliberate.** The comment at `saffron/cell/session.py:2303-2307` says why: the
local tally loses the walled turn. Take the figure that path already computes
rather than the local variable.

**Correct the stale comment while you are in it.** `saffron/cell/session.py:2268`
says "a tenth kind" and there are ten kinds today. Once this spec lands the
count changes again, so leave no sentence claiming a number that was never
right.

**`census` compares test names, so rename nothing.** Two queued specs also name
`tests/test_session.py`, and one names `tests/test_events.py`. Keep the diff to
the new tests plus the call sites this spec replaces.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
