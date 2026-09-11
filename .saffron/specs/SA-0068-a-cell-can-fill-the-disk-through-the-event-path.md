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
      A parsed cell event larger than the bound is persisted bounded. What an
      `Agent` line stores of the cell's event is at most the bound, counted in
      characters of the event's JSON serialization, the unit the raw `line` is
      already sliced in. The written line is then at most a small constant
      multiple of that, because JSON escaping can multiply a character when it
      is written, plus the envelope. It is not five megabytes. The witness feeds
      five megabytes of ordinary text and five megabytes of `"`. The raw path is
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
      drift, and the item names "one value, both paths" as the open half. The
      witness patches that one value in `saffron.events` to a small number and
      shows that a raw line through `run_agent` and an oversized event through
      `EventLog.append` are both cut at the patched value.
    witness: tests/test_implement.py::test_the_raw_line_and_the_event_are_bounded_by_one_value
  - claim: >-
      Only what is persisted is bounded. `run_agent` still reads the whole event
      it parsed, while what reaches `events.jsonl` is bounded. The witness drives
      `run_agent` with an `emit` that appends to a real `EventLog`, then asserts
      both halves: the text it accumulates, the result it completes on and the
      rate limit it reports are the cell's full values, and the line `read_log`
      returns is bounded.
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
      or depth, and still does not write one it cannot copy.
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
stored, not what is printed. Bounding in `EventLog.append` leaves the attended
terminal unchanged, because every emit fan-out calls `describe` before it
appends.

**Other cell-authored strings.** `Terminal.detail` on a rejected plan and the
detail of a REVIEW re-prompt also carry text that came out of a cell, and this
spec does not bound them. The route it closes is the `Agent` event.

**Rotation, compression, or a per-file cap.** `EventLog`'s own `ponytail:`
names one file per task with no rotation. Bounding each event bounds each line,
which is the hole a single cell can open. A cap on the whole file is a different
decision.

**A new event kind.** Adding one is a vocabulary change (`CONTEXT.md` is
forbidden here).

## Notes for the agent

**The bounding code is new, so its criteria carry witnesses and no mutants.**

**Every new witness must fail with `events.py` and `implement.py` reverted, not
merely be missing at base.** The `revert` gate re-runs each new witness against
the reverted source and blocks any that still pass. The fourth criterion's
first half is true today, which is why its witness must also assert the bounded
line on disk. Resist extra tests such as "an event exactly at the bound is
verbatim": that passes reverted. Import new names inside tests, not at module
scope. A module-scope import of a name you add makes the reverted run a
collection error, which `revert` reads as `skip`.

**Keep every `Agent` field at its annotated type.** `event` stays a dict or
`None`, never a string holding truncated JSON. A string under `event` is
dropped by `saffron watch` and makes `describe` raise, and `SA-0070`, queued
behind this spec, makes `read_log` drop any field of the wrong type, so a
bounded event stored that way would vanish on read. If the bounded form needs a
new field, give it a type and a default: `tests/test_watch.py` and
`tests/test_session.py` build `Agent` and are outside `touches`. Say in the
`Agent` docstring what `describe` renders for a bounded event. `saffron watch`
shows the stored form, not what the attended terminal showed.

**Where the bound belongs.** The item says bounding the event path needs
`saffron/events.py`, and the first criterion's witness lives in
`tests/test_events.py`. `implement.py` already imports from `events.py`, so the
one value can live there, and `_quarantined` can read it from there at call
time. The reverse would make core depend on a phase. The preserved test
`test_a_line_that_is_not_an_event_is_bounded_at_capture` reads
`implement.QUARANTINE_BYTES` by that name, so the name must stay reachable from
`implement` wherever the value moves.

**Measure the event the way the first criterion says.** The unit is the length
of `json.dumps(event.event)`, compared with the same value the raw `line` is
sliced to. It is not the length of the whole written line: a raw line already
at the bound would then be cut a second time by `append`.

**`asdict` is the statement reading hostile input, and it stays on the path.**
`EventLog.append`'s own comment measures it: `asdict` raises `RecursionError` on
nesting that `json.loads` accepted. Whatever measures an event's size must sit
inside the same `try`. The last preserved witness also asserts that a depth-1000
event is *not* written, which holds only because `asdict` raises on it.
Dropping `asdict` to avoid copying five megabytes before bounding is a natural
optimisation, and it fails that witness.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. Keep test docstrings to the sentence that says why.
