---
id: SA-0080
title: a follower re-reads and re-parses a task's whole event log on every poll, so following a night costs O(n²)
type: bug
priority: 3
depends_on: []
touches:
  - saffron/events.py
  - saffron/watch.py
  - tests/test_events.py
  - tests/test_watch.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - spikes/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/intake.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 40
acceptance:
  - claim: >-
      Each poll of a follower reads only what was appended to the log since the
      poll before it. Nothing it has already read is read or parsed again.
      Today every poll re-reads the whole file: one read of a 37 MB log was
      measured at 5.7s, and past that a one-second poll interval falls
      permanently behind.
    witness: tests/test_watch.py::test_a_poll_reads_only_what_was_appended_since_the_last
  - claim: >-
      A line one poll catches half-written is rendered once, whole, by the
      poll after the write completes, as it is today.
    witness: tests/test_watch.py::test_a_line_completed_between_polls_renders_once_and_whole
    preserves: true
  - claim: >-
      A follower still renders each event once and never repeats a line it
      has already rendered, as it does today.
    witness: tests/test_watch.py::test_following_emits_only_events_that_arrived_since_the_last_poll
    preserves: true
  - claim: >-
      Reading a task's log the way every other caller reads it still returns
      every whole event and drops a truncated final line, as it does today.
    witness: tests/test_events.py::test_read_log_drops_a_truncated_final_line
    preserves: true
---

## Context

`docs/BACKLOG.md` item **62**, measured 2026-09-04 while reviewing `SA-0053`
(PR #119). A `ponytail:` in `follow` (`saffron/watch.py`) names the problem.

`watch.follow` calls `read_log` once per poll, then skips the events it has
already rendered by count. `read_log` has no offset: it reads and parses the
entire `events.jsonl` every time. So following a task costs O(n²) over a night.
One `read_log` of a 37 MB, 160k-line log was measured at **5.7s**. Past that,
the default one-second interval falls permanently behind and keeps a core busy
re-parsing lines it already rendered. `events.py`'s own `ponytail:` gives "tens
of MB a night" as the ceiling, so this is inside the range the log is designed
for.

## Problem

The follower that `saffron watch` exists to provide cannot keep up with the
log size this repo designs for, on the night nobody is watching the terminal.

## Out of scope

**Task boundaries in the log.** A spec driven twice writes both tasks into one
file. That is `SA-0081`, which builds on this.

**Rotation, compression or a size cap on `events.jsonl`.** That is the other
`ponytail:` in `events.py`, and it is about size, not reading.

**A log truncated or replaced under a running follower.** `EventLog` only
appends. What a follower does when the file shrinks is a question for when
something shrinks it.

## Notes for the agent

**The first criterion's change is new code, so it declares a witness and no
mutant.** `witness` will report `skip` on this spec, and that is expected. The
other three are `preserves`: their witnesses already exist and pass.
`test_a_line_completed_between_polls_renders_once_and_whole` was written ahead
of this spec for that purpose.

**The witness must fail with the source reverted, not merely be missing at
base.** Observe the property through behaviour. One way: after a poll, overwrite
bytes the follower has already read, in place, at the same length and keeping
the newlines, with bytes that do not parse, then append a new event. A follower
that resumes where it stopped renders the new event. A whole-file re-read drops
the overwritten lines, so its count-based slice skips the new event. Import
nothing new at module scope, because a module-scope import of a name you add
turns the reverted run into a collection error, which `revert` reads as `skip`.

**One parser.** Whatever reads from an offset shares `read_log`'s per-line
tolerance: truncated final line, unknown kind, wrong shape. It must not be a
second parser in `watch.py`. A second parser beside `read_log` is the same
defect as a second renderer beside `describe`, which is what `SA-0053` was
written to avoid.

**A partial final line leaves the offset before it.** If the offset moves past
it, the next poll resumes mid-object and loses that event. The second
criterion's witness guards this.

**Offsets are bytes, not characters.** Read the file in binary and decode each
whole line. A multi-byte character anywhere before the offset makes character
counts and byte counts disagree. This is reasoned, not measured.

**Every other caller of `read_log` reads a whole log once**, including `cli`,
the report and the phases' tests. Keep the call shape they use working, as the
fourth criterion requires, rather than changing its return type under them.

**Take the `ponytail:` out of `follow`** once it no longer describes the code.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
