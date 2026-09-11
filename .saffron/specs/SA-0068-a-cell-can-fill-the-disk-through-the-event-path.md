---
id: SA-0068
title: a cell's parsed events reach events.jsonl unbounded, while its raw lines are capped
type: bug
priority: 1
depends_on: []
touches:
  - saffron/events.py
  - saffron/phases/implement.py
  - tests/test_events.py
  - tests/test_implement.py
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
  - saffron/agents/**
  - saffron/watch.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 50
risk: standard
acceptance:
  - claim: >-
      A parsed cell event larger than the bound is persisted bounded. One `text`
      event carrying five megabytes writes a line to `events.jsonl` no longer
      than the bound plus a fixed envelope, not five megabytes. The raw path is
      already bounded at capture, and wrapping the same payload in nine bytes of
      JSON walks straight past that bound. This closes that route.
    witness: tests/test_events.py::test_an_oversized_agent_event_is_bounded_on_disk
  - claim: >-
      A bounded event says that it was bounded, and how large it was, when read
      back. Truncating in silence makes a record that looks complete and is not,
      which is worse than the unbounded line it replaces. The log is evidence
      (item 46, decided 2026-09-04), so a reader must be able to tell a cut
      event from a whole one.
    witness: tests/test_events.py::test_a_bounded_agent_event_says_it_was_bounded
  - claim: >-
      The raw line and the parsed event are bounded by one value, not two
      constants that agree today. Two numbers for one decision is how the paths
      drift, and the item names "one value, both paths" as the open half.
    witness: tests/test_implement.py::test_the_raw_line_and_the_event_are_bounded_by_one_value
  - claim: >-
      Only what is persisted is bounded. `run_agent` still reads the whole event
      it parsed: the text it accumulates, the result it completes on, and the
      rate limit it reports are the cell's full values, not the stored ones.
      Bounding the host's own reading of a turn would be a behaviour change this
      item did not ask for.
    witness: tests/test_implement.py::test_a_bounded_event_still_reaches_the_attempt_result_whole
  - claim: >-
      An event under the bound is still written verbatim.
    witness: tests/test_events.py::test_agent_carries_a_parsed_dict_verbatim
    preserves: true
  - claim: >-
      The raw path stays bounded at capture, as it is today.
    witness: tests/test_implement.py::test_a_line_that_is_not_an_event_is_bounded_at_capture
    preserves: true
  - claim: >-
      `append` still never raises on a dict a cell authored, whatever its size
      or depth.
    witness: tests/test_events.py::test_append_never_raises_on_a_dict_a_cell_authored
    preserves: true
---

## Context

`docs/BACKLOG.md` item **46**, the size half. **Decided 2026-09-04: the log is
evidence, not an operator's record**, so it keeps full content and takes a size
cap instead of being reduced to rendered lines. The deciding argument is §9's
v1 criterion. The defining property of the milestone is that nobody was
watching, and a log reduced to bounded renderings would throw away the only
account of the night it matters most on.

`SA-0041` made `run_agent` emit the parsed cell event verbatim under
`Agent.event`, which was right. The side effect, raised by that run's contract
lens: what reaches persistence changed shape. `SA-0041` then bounded the
*raw* quarantined line at capture (`implement.QUARANTINE_BYTES`, 8192) after a
review measured five megabytes of stdout writing five megabytes of log. It
could not bound the event path, because `saffron/events.py` was forbidden to
it, and its own docstring on `_quarantined` says so:

> Measured on one 5 MB stdout line: 5 MB written unbounded, 8 KB now; the same
> line as `{"type":"text",...}` still writes 5 MB. Backlog item 46 is where
> both paths get one answer.

This spec is that answer.

## Problem

A cell is untrusted, and its stdout is authored by whatever runs in it. Today it
decides how much the host writes to `~/.saffron/batches/v0/<SPEC-ID>/events.jsonl`,
and the only thing standing between a cell and the host's disk is whether it
remembered to wrap its output in JSON.

## Out of scope

**The `secrets` gate's reach.** The other half of item 46 is that a credential
a cell printed is persisted host-side and scanned by nothing. The `secrets` gate
is not built yet, so there is nothing to extend. That half stays on the item.

**What the terminal shows.** `describe` already clips what it renders, and the
clipping of its unclipped branches is `SA-0070`'s. This spec bounds what is
stored, not what is printed.

**Rotation, compression, or a per-file cap.** `EventLog`'s own `ponytail:`
names one file per task with no rotation. Bounding each event bounds each line,
which is the hole a single cell can open. A cap on the whole file is a different
decision.

**A new event kind.** Adding one is a vocabulary change (`CONTEXT.md` is
forbidden here). If the bounded form needs somewhere to say it was cut, a field
on `Agent` that round-trips through `read_log` is acceptable. So is a shape that
uses the fields `Agent` already has.

## Notes for the agent

**This spec restructures existing code, so its criteria carry witnesses and no
mutants.** The constant may move, and a mutant pinned to its current spelling
would stop matching the moment it did.

**Where the bound belongs.** The item says bounding the event path needs
`saffron/events.py`, and the first criterion's witness lives in
`tests/test_events.py`. `implement.py` already imports from `events.py`, so the
one value can live there and be imported back. The reverse would make core
depend on a phase. The preserved test
`test_a_line_that_is_not_an_event_is_bounded_at_capture` reads
`implement.QUARANTINE_BYTES` by that name, so the name must stay reachable from
`implement` wherever the value moves.

**Measure the way the raw path measures.** The raw path slices the line, so its
bound is in characters of the line. Bound the event on its serialized form, by
the same unit, so "one value" means one thing.

**`asdict` is the statement reading hostile input.** `EventLog.append`'s own
comment measures it: `asdict` raises `RecursionError` on nesting that
`json.loads` accepted. Whatever measures an event's size must sit inside the
same `try`, or a deep enough dict escapes the never-raises contract the last
preserved criterion holds.
