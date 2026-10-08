---
id: SA-0250
title: A bounded agent event drops its per-message token counts from the event log
type: bug
priority: 2
depends_on: [SA-0242]
estimated_lines: 136
estimate_measured: true
touches:
  - saffron/events.py
  - saffron/phases/implement.py
  - tests/test_events.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cell/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/watch.py
  - saffron/projection.py
  - saffron/task.py
  - tests/test_implement.py
  - tests/test_agent_runner.py
  - tests/test_watch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 21
max_attempts: 3
max_turns: 100
acceptance:
  - claim: >-
      When `EventLog.append` bounds an `Agent` event, the bounded event keeps
      each of `input_tokens`, `cache_read_input_tokens`,
      `cache_creation_input_tokens` and `model` that the cell event carried,
      within the bound criterion 3 names.
      They sit verbatim in a `usage` field on the bounded event, and
      `read_log` returns them. A key the cell event lacked is absent from
      `usage`, and a carried null stays null. No other key of the cell
      event is kept. The witness drives all four keys with values, all four
      null, and `input_tokens` alone at 0.
    witness: tests/test_events.py::test_a_bounded_event_keeps_its_per_turn_counts_and_model
    wrong_versions:
      - A `usage` kept only when all four keys are present, which loses the lone `input_tokens`.
      - A null count dropped from `usage` rather than kept as null.
      - A count of 0 dropped, as a truthiness test on the value does.
      - An absent key written into `usage` as null, which reads the lone `input_tokens` case as four keys.
      - "`model` left off, so `usage` holds the three counts alone."
      - One of the three counts left off.
      - The cell event's `type` kept in `usage` beside the four.
  - claim: >-
      A bounded event whose cell event carried none of the four keys has a
      null `usage`. An event under the bound is written as before, its
      counts inside `event` and its `usage` null.
    witness: tests/test_events.py::test_only_a_bounded_event_with_counts_carries_them
    wrong_versions:
      - An empty dict written for `usage` when none of the four was carried.
      - "`usage` filled on every `Agent` event, the unbounded ones included."
      - The counts moved out of an unbounded event's `event` dict into `usage`.
  - claim: >-
      The kept keys are held to their own bound. When their `json.dumps`
      exceeds 512 characters, `usage` is null and the bounded event is
      still written, with `EventLog.failed` unset. The witness drives a
      kept `model` whose `usage` serializes to 512 characters and one to
      513. It also drives an `input_tokens` that is a list nested 1000 deep
      and a 5 MB `model`. Every line it writes stays under `BOUND_CHARS * 2
      + 1024` characters.
    witness: tests/test_events.py::test_carried_counts_are_held_to_their_own_bound
    wrong_versions:
      - No bound on `usage`, so the 1000-deep list reaches `asdict` and the whole event is lost.
      - "`usage` held to `BOUND_CHARS` rather than 512, which keeps the 513 case and the 1000-deep list."
      - The bound applied with `>=`, which drops the 512 case.
      - A bounded event dropped from the log when its keys exceed the bound, rather than written with a null `usage`.
  - claim: >-
      `describe` renders a bounded event that carries a `usage` as the line
      it renders without one. That is `agent: (bounded, N chars) ` followed
      by the stored line cut to 160 characters, and no count.
    witness: tests/test_events.py::test_a_bounded_event_renders_the_same_line_with_counts
    mutant:
      file: saffron/events.py
      find: '{event.original_chars} chars) "'
      replace: '{event.original_chars} chars) {event.usage} "'
    wrong_versions:
      - The counts appended to the rendered line.
  - claim: >-
      A turn that ends with no `result` event still carries the cost floor
      its per-message counts price, once the host's tuple of the three
      count names lives in `saffron/events.py`.
    witness: tests/test_implement.py::test_a_turn_with_no_result_event_carries_the_floor_its_usage_prices
    preserves: true
---

## Context

Backlog item **146**. It cites `DESIGN.md` §7.1, and the event log is
§4.7. Item 126 waits on this series to measure the REVIEW lenses' cache
reads.

**Where the counts start.** The runner names three per-message counts in
`_STEP_USAGE_KEYS` (`images/agent_runner.py:37-41`). It puts them on the
first event an assistant message produces (`images/agent_runner.py:163`).
It puts the message's `model` on that same event
(`images/agent_runner.py:166`). For a text block that event holds the whole
message text.

**Where the log drops them.** `EventLog.append` runs
`json.dumps(event.event)` on an `Agent` event (`saffron/events.py:423`). Past `BOUND_CHARS`, 8192
(`saffron/events.py:61`), it replaces the event with `event=None` and the
serialization cut to `BOUND_CHARS` (`saffron/events.py:424-431`). The
dataclass's fields end at `original_chars`, and none holds a count
(`saffron/events.py:303-311`). So a long message's counts reach the log
only as cut text, and often not at all.

**What the cut does not lose.** `run_agent` prices each non-result event
with `_priced_usd` (`saffron/phases/implement.py:351-353`). It emits the
event after that (`saffron/phases/implement.py:357`). The emit reaches
`log.append(event)` in `_default_emit` (`saffron/cell/session.py:101`). So
`SA-0206`'s floor prices the counts before the bound, and cost is not lost.
The `result` event's totals are small and survive. What the log loses is
the per-message series, on its longest messages.

**What reads the series today.** Nothing in code.

- `describe` renders a bounded event from `original_chars` and `line`
  alone (`saffron/events.py:810-815`). No count name appears in
  `saffron/events.py`.
- `saffron watch` prints `describe` lines (`saffron/watch.py:115`).
- The cell-watch hook drops every `Agent` line before it reads the log
  (`.claude/skills/cell-watch/hooks/register.tsx:49`).
- `saffron/projection.py` reads `Ceilings`, `PhaseStart` and `Teardown`
  events alone (`saffron/projection.py:181`). Nothing under `saffron/view/`
  names `Agent`.

**The host's copy of the names.** `saffron/phases/implement.py` repeats
the runner's tuple as `_STEP_USAGE_KEYS` (`saffron/phases/implement.py:126-132`).
`_priced_usd` loops over `_STEP_USAGE_KEYS` (`saffron/phases/implement.py:153`).
The module runs `from saffron import events` (`saffron/phases/implement.py:17`).
So `events.py` cannot import the tuple from `implement.py` without a cycle.

**Why the bound on `usage` is 512.** `asdict` copies a nested dict before
`json.dumps` runs. At 1000 deep it raises, and the event is lost
(`tests/test_events.py:822-842`, measured there: 500 is fine). A bounded
event survives that today, since `asdict` then copies a string
(`saffron/events.py:433-436`). A list nested 256 deep serializes to 512
characters, well inside the measured 500.

## Problem

The per-message counts ride on the event most likely to be cut. A long
assistant message is the turn whose counts matter most, and the bound
replaces exactly that event with cut text. The log then holds the
per-message series with holes at its most useful points.

## Out of scope

- **Tying the two key tuples.** `images/agent_runner.py:37-41` still
  defines its own tuple, and nothing compares it with `STEP_USAGE_KEYS`.
  Backlog item b-0efc31 owns that test. Carry the comment that names the
  runner's tuple as the source over to `STEP_USAGE_KEYS` in `events.py`.
- **The runner.** `images/agent_runner.py` keeps placing the counts on the
  first event. Changing it means an image rebuild, and the host can keep
  them alone.
- **Rendering the counts.** `describe` and `saffron watch` show no count
  today and keep showing none.
- **A reader of the series.** Item 126 reads one night's log by hand.
- **The raw-line quarantine.** `_quarantined` stores a line that was not
  JSON (`saffron/phases/implement.py:240-258`). It holds no counts.
- **`DESIGN.md` §4.7.** It is protected. The operator edits its text by
  hand.

## Notes for the agent

**Which criteria are new code.** Criteria 1 to 3 build behaviour that does
not exist, so each declares a witness and no mutant. Expect `witness` to
report `skip` for them. Criterion 4 pins `describe`'s existing bounded
branch, which this change must leave alone, so it declares a mutant.
Criterion 5 is an existing test that guards the tuple's move.

**The field.** Add `usage: dict | None = None` as the last field of
`Agent`. `read_log` already accepts a `dict | None` field through
`_shape_ok`. Say in the `Agent` docstring that a bounded event keeps its
counts and `model` in `usage`. Keep that docstring within its current
length plus two lines.

**The names.** Move the tuple into `saffron/events.py` as a public
`STEP_USAGE_KEYS`, beside `BOUND_CHARS`. Delete the copy in
`saffron/phases/implement.py`, and read `events.STEP_USAGE_KEYS` there
instead. Name `model` beside the tuple when you build `usage`, not inside
it, since `_priced_usd` loops the tuple over counts.

**The bound.** In `EventLog.append`, pass the kept keys into the same
`replace` call that sets `bounded=True`. Build them in a small helper. It
keeps each key the cell event has, verbatim. It returns `None` when none
is present, or when `json.dumps` of the result exceeds 512 characters.
Leave the unbounded path alone.

**The witnesses.** Add the four tests to `tests/test_events.py`, after the
SA-0068 block. Import `BOUND_CHARS` inside each test body, as that block
does, so the reverted run fails on the missing field rather than on
collection. Build each bounded event as a `text` event whose text is
twice `BOUND_CHARS`, with the keys added beside it. Read back through the
file's `_read(tmp_path, Agent)` helper.

- Criterion 1 appends three bounded events. The first carries the four
  keys as 101, 202, 303 and `"claude-sonnet-5"`. The second carries the
  four as null. The third carries `input_tokens` at 0 alone. Assert each
  `usage` with `==` against the dict it carried.
- Criterion 2 appends a bounded event with none of the keys, then an
  unbounded `text` event carrying `input_tokens` and `model`. Assert the
  first `usage` is `None`. Assert the second is not bounded, its `event`
  equals what was appended, and its `usage` is `None`.
- Criterion 3 pads `model` so `{"model": ...}` serializes to exactly 512
  characters, then 513. It also appends a 1000-deep `input_tokens` from
  `json.loads("[" * 1000 + "]" * 1000)` and a `model` of 5,000,000
  characters. Assert `log.failed` is false and four bounded events read
  back. Assert the 512 case keeps its `usage` and the other three read
  `None`. Assert every written line is under `BOUND_CHARS * 2 + 1024`.
- Criterion 4 builds the `Agent` directly, as
  `test_a_bounded_event_renders_its_size_and_a_terminal_cut` does, with
  `usage={"input_tokens": 1, "model": "m"}`. Assert the same rendered line
  that test asserts.

Commit after each witness passes. Uncommitted work dies with the cell.
