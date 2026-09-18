---
id: SA-0103
title: EventLog.failed is the breadcrumb for a log that stopped writing and nothing reads it, so a disk-full night reads as a quiet one
type: bug
priority: 1
depends_on:
  - SA-0100
touches:
  - saffron/task.py
  - tests/test_task.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/events.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/watch.py
  - saffron/replay.py
budget_usd: 12
max_turns: 80
acceptance:
  - claim: >-
      A task whose event log stops accepting writes says so on the terminal,
      naming the log that stopped growing, and a task whose log wrote cleanly
      says nothing. Today neither case produces a word, because the flag that
      records the failure has no reader.
    witness: tests/test_task.py::test_a_log_that_stopped_writing_says_so_and_a_clean_one_does_not
  - claim: >-
      A task whose log refuses many writes warns once, rather than once per lost
      event. With several events emitted through the task's own emit and every
      append failing, the terminal carries exactly one warning line.
    witness: tests/test_task.py::test_a_log_that_refused_every_write_warns_once
  - claim: >-
      A task whose log fails its first write still warns, and the warning is
      never appended to the log. With a log that refuses its first append and
      accepts the rest, the terminal carries the warning and the log file holds no
      event describing its own failure.
    witness: tests/test_task.py::test_a_log_that_failed_on_its_first_write_still_warns
---

## Context

`events.jsonl` is a batch tree artifact, which §4.1 makes the record an operator
greps when the ledger itself is what broke. `EventLog` was built with this
failure in mind, and its own comments say so twice.

`saffron/events.py:388` sets the flag in the constructor. The comment above it
says "A disk-full night must not render as a night in which nothing happened". It
adds that `append` "never raises", which is "how anyone can tell". The `except`
clause in `append` catches `OSError`, `RecursionError`, `TypeError` and
`ValueError`, then sets the flag at `saffron/events.py:426` and returns. The
comment there calls it "the breadcrumb".

`saffron/cell/session.py:77-78`, inside `_default_emit`'s docstring, repeats the
reasoning. A disk-full night "just stops growing `events.jsonl`, which
`EventLog.failed` is the breadcrumb for".

No production code reads it. Nothing under `saffron/` reads the attribute at
all, and the only near miss is an unrelated `proxy.failed_egress` at
`saffron/cell/session.py:963`. Two tests read it, and neither surfaces it.
`tests/test_events.py:802` asserts the flag is set after a swallowed write, and
`tests/test_events.py:2495` asserts it is clear. So the flag is observable to the
suite and to nobody driving a task.

Four places own a log: `saffron/task.py:254`, `saffron/cell/session.py:802`, and
`saffron/phases/package.py:624` and `:1046`. The production one is the first.
`saffron/task.py:249-260` builds the log and a closure `emit` for a caller that
passed none, then hands that closure down. So `session._default_emit` is not the
seam a driven cell uses, and neither are the two fallbacks in
`saffron/phases/package.py`. Its own comment names the shape: "Print plus the task's
own log, the shape `session._default_emit` and `package()` both default to."

So a night where the disk filled produces a task that reaches its terminal state
with a truncated log, and says nothing about the truncation. `CLAUDE.md` names
the stake: under launchd the terminal scroll is "the night's only
human-readable record", and the durable log is what survives a SIGTERM. When
both are short, nothing distinguishes a quiet night from a lost one.

This is the neighbour of backlog item **46**, which `PRIORITY.md` places in
tier 1 and calls "the only account of a night nobody watched". Item 46 bounds
and scans what the log holds. This spec is about the log that holds nothing and
does not say so.

## Problem

- **A truncated log is indistinguishable from a short one.** Both render as
  fewer lines, and no line says which happened.
- **The flag exists to answer that and answers nobody.** Two comments promise a
  breadcrumb that no code follows.
- **This fails on the unattended nights.** A disk filling is the failure of a
  long night, and the night's record is what it destroys.
- **The failure is silent by design, and the design was only half built.**
  `append` never raising is correct. Never raising and never reporting is not.

## Out of scope

**`saffron/events.py`.** It is forbidden. `append` keeps swallowing the write
and keeps setting the flag. `tests/test_events.py:408`,
`test_event_log_write_failure_raises_nothing`, states the property this spec must
not break, and it runs under the blocking `tests` gate. Do not make a failed
write raise.

**The other three log owners.** `saffron/cell/session.py` and
`saffron/phases/package.py` are both forbidden. The production seam is
`saffron/task.py`, and widening this to four call sites makes a one-line read
into a refactor.

**Counting the lost events.** That needs a counter on `EventLog`, which lives in
a forbidden file. One honest warning beats a count this spec cannot reach.

**Bounding or scanning what the log holds.** That is item 46, and it is a
different problem with its own tier-1 entry.

**Failing the task.** A log that cannot be written is not a reason to throw away
a task that otherwise passed its gates. `append`'s own docstring says the caller
"has nothing useful to do with the failure either way", and that stays true of
the exit code. Report it, and change no state.

## Notes for the agent

**This spec's change is new code.** All three criteria declare a witness and no
mutant. No reader exists, so nothing pins honestly, and the wording of the
warning is yours. Expect `witness` to report `skip` for all three.

**The warning cannot go through the log.** The log is what failed, so a warning
appended to it is lost by the same fault. It goes to the terminal, beside the
line `describe` produced, and nowhere else.

**Read the flag around the write.** Do not wait for the end of the run.
Comparing the flag before and after each `append` catches the moment it flips.
That needs no new state on `EventLog`, and warns once without a counter. A check
placed after the task finishes also works, and reports later than it could. A
check that runs once at the start catches nothing.

**Criterion 2's wrong implementation is a warning per lost event.** A disk that
filled refuses every write for the rest of the night. A warning inside the
failure branch then prints thousands of times and buries the task.

**Criterion 2 needs more than one event to reach the closure.** Otherwise it
checks nothing. `run_task` emits one event of its own on the ordinary path, the
`Ceilings` line at `saffron/task.py:262`. Every other event arrives from
`run_one_cell` and from PACKAGE, both of which your test doubles. So a double
that emits nothing leaves a one-event stream, where warning per failed append and
warning once are the same single line. Make the `run_one_cell` double emit at
least three events through the `emit` it is handed, and assert the terminal
carries exactly one warning.

**Criterion 3's wrong implementation is a check placed after the first
successful append.** The first event a task emits is its `Ceilings` line, at
`saffron/task.py:262`. A log unwritable from the start fails on that one.

**Criterion 3's log fails its first append by count.** That append is the
`Ceilings` emit at `saffron/task.py:262`, which runs before `run_one_cell`. A
warning routed through `emit` is appended inside that same first call. Consider
a log made unwritable on disk, such as a directory where the file goes
(`tests/test_events.py:2117`). It is still unwritable when the warning's own
append runs. Removing the directory inside the `run_one_cell` double comes too
late, and the wrong implementation passes. `saffron/task.py` imports `EventLog`
into its own namespace and builds the log there. So replace
`saffron.task.EventLog` with a subclass. Its first `append` sets
`self.failed = True` and returns without writing. Its later appends call the
real one. Then assert the terminal carries the warning. Also assert that
`events.jsonl` holds exactly the events the `run_one_cell` double emitted, in
order, and nothing else.

**Extend `_drive` in `tests/test_task.py`, and write no second driver.**
`SA-0100` made `_drive`. It builds a `CellOutcome` and replaces
`saffron.task.run_one_cell` with a double that emits nothing. Then it calls
`run_task` with no `emit`, so the closure under test is the one that runs.
Criteria 2 and 3 need a double that emits through the `emit` it is handed. Give
`_drive` an optional list of events for its double to emit through `k["emit"]`
before it returns the outcome. Every state other than `READY_FOR_REVIEW` also
reaches `push_unpackaged_work`, which `_push` replaces.

**Two stale comments in forbidden files contradict the seam above.** Both name
`cli.py`. `saffron/cell/session.py:73-75` describes `_default_emit` as the
fallback for "every direct caller today, and `cli.py`, which is forbidden here
and never passes `emit`". `tests/test_session.py:984-985` says `use_default_emit` calls
"`run_one_cell` exactly as `cli.py` does". Neither is true at this base:
`saffron/cli.py:368` and `:410` call `run_task`, never `run_one_cell`. Both files
are forbidden here, so leave them, and do not let either talk you out of reading
`task.py` for yourself.

**Name the log without reaching into it.** `EventLog` keeps its path private at
`saffron/events.py:385`, and `saffron/events.py` is forbidden, so there is no
accessor to add. Re-derive the path from `out_dir` and the spec id, which the
closure already has in scope, rather than reading the private attribute.

**Do not reach into `os.environ` or the real filesystem outside `tmp_path`.**
`saffron/task.py`'s module docstring states the rule: a module that reaches into
the environment is one a test has to reach into too.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
