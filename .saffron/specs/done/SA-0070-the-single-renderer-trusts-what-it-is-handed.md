---
id: SA-0070
title: the single renderer raises on input it is handed and prints a cell's control bytes to the operator's terminal
type: bug
priority: 2
depends_on:
  - SA-0068
touches:
  - saffron/events.py
  - tests/test_events.py
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
  - saffron/watch.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
  - tests/fixtures/**
budget_usd: 6
max_attempts: 3
max_turns: 50
risk: standard
acceptance:
  - claim: >-
      `read_log` drops an event whose field is present with the wrong shape,
      exactly as it already drops one whose required field is missing, and the
      lines around it survive. Today a hand-edited or corrupt line round-trips
      into `Agent(event='x')`, and `describe` then raises `AttributeError` on
      `.get`, taking down every caller but the one that guards for it.
    witness: tests/test_events.py::test_a_field_of_the_wrong_shape_drops_its_event_not_the_file
  - claim: >-
      `describe` renders every event it can be handed without raising,
      including the ones a type check cannot catch: a `Baseline` whose gate and
      status lists differ in length, and a `rate_limit` payload whose
      `resets_at` is a string, a list, an integer too large for a timestamp, or
      not a number. The second case reaches `describe` from a live cell, not
      only from a corrupt log, because `run_agent`'s `emit` renders every event
      as it arrives. Its contract is "any `Event`", or it is not the single
      renderer the repo relies on.
    witness: tests/test_events.py::test_describe_renders_whatever_it_is_handed
  - claim: >-
      Every field a cell authored is clipped where it is rendered. Today the
      `text` branch clips at 160, and `tool_use` clips its input at 120 but not
      its `name`. `tool_use.name`, the `result` branch, the `error` branch, the
      `rate_limit` branch and the fallback clip nothing, so a five-thousand-
      character error from a cell reaches the terminal whole. Each cell-authored
      field is clipped at 160, the bound `text` already uses. Host-authored
      text, such as the `, resets …` suffix, is not clipped.
    witness: tests/test_events.py::test_every_cell_authored_field_is_clipped
  - claim: >-
      No control character from an `Agent` event reaches the rendered line.
      Each character from U+0000 to U+001F, and U+007F, in cell-authored
      content is replaced with a space. An error event carrying an escape
      sequence currently clears the operator's screen and retitles their
      terminal, and `saffron watch` can replay that into a fresh terminal long
      after the run. The strip happens once, in the renderer, not in each
      caller.
    witness: tests/test_events.py::test_an_agent_payload_cannot_put_control_characters_on_a_terminal
  - claim: >-
      Every line the agent renderer produces today for an ordinary payload is
      unchanged, including the 160 and 120 bounds.
    witness: tests/test_events.py::test_the_duplicated_agent_renderer_still_matches_its_original
    preserves: true
  - claim: >-
      A field a newer Saffron added is still dropped without dropping its event.
      Checking the shape of known fields must not start rejecting unknown ones.
    witness: tests/test_events.py::test_a_field_a_newer_saffron_added_does_not_delete_the_event
    preserves: true
  - claim: >-
      What an attended run prints for the kinds the golden fixture captured is
      unchanged, line for line.
    witness: tests/test_events.py::test_watch_output_matches_the_golden_fixture
    preserves: true
---

## Context

`docs/BACKLOG.md` items **61** and **63**, both found reviewing `SA-0053`
(PR #119) and both fixed *around* rather than fixed, because
`saffron/events.py` was forbidden to that spec. They are one spec because they
are one property: `describe` is the only renderer, and it has to be safe on
anything it is handed.

**Item 61, measured:**

```
read_log tolerates it: [Agent(timestamp=1.0, spec_id='T1', raw=False, event='x', …)]
describe RAISED: AttributeError 'str' object has no attribute 'get'
```

`read_log` type-checks nothing. It is `cls(**obj)` onto a plain dataclass, so
per-line corruption defeats the per-line tolerance its own docstring promises.
`watch.py` guards its own call (`_is_malformed`). Every other caller of
`describe` does not.

**Measured when this spec was reviewed, and not in the item:** right-shaped
input also raises. `Baseline(gates=('a', 'b'), statuses=('pass',))` raises
`ValueError` at the `zip(..., strict=True)` in `describe`. A `rate_limit` event
whose `resets_at` is `"soon"` or `[1]` raises `TypeError` in `_when`, `10**20`
raises `OverflowError`, and `NaN` raises `ValueError`.

**Item 63:** `_describe_agent_event` clips `text` at 160 and the input of
`tool_use` at 120, and nothing else. An `Agent` event carrying
`{"type": "error", "error": "\x1b[2J\x1b]0;…\x07" + "A"*5000}` renders with the
escape bytes intact. `text` passes ESC and BEL through as well, because
`str.split` collapses only whitespace. The content is authored inside a cell,
and a cell is untrusted.

## Problem

Two properties the repo assumes of its renderer are not true: that it cannot
raise, and that what it prints is bounded and inert. The first takes down a
caller on a corrupt line, or on a live cell's malformed event. The second hands
an untrusted cell the operator's terminal.

## Out of scope

**`watch.py`'s own guard.** `_is_malformed` becomes redundant once `read_log`
refuses the shape. Leave it: `saffron/watch.py` is forbidden, and a redundant
guard is not a defect. `watch.py` and `tests/test_watch.py` both carry a
sentence saying `read_log` type-checks nothing, which becomes stale. That is
expected, and it is not yours to fix.

**Other kinds' cell-authored text.** `Terminal.detail` on a rejected plan and
`PhaseStart.detail` can carry paths an agent wrote, and they render unstripped.
This spec covers the `Agent` event.

**C1 controls and full ANSI parsing.** A sequence introduced by a C1 byte is a
real but narrower case. File it in your notes if you think it matters. Do not
widen this spec to cover it.

**Checking a `Literal` field's membership.** A `TerminalReason` that is a string
but not one of the five is the right shape carrying an unknown value. `describe`
already has a fallback for it, and a newer Saffron adding a value is the
forward-compatibility case `read_log` exists to allow.

**The golden fixture.** `tests/fixtures/**` is forbidden. It holds no `agent:`
line and only the joined `baseline:` line, so it guards less of this change than
its name suggests. The parametrized `test_describe_renders_every_kind_and_variant`
is the test that sees a rendering change, and it has to keep passing.

## Notes for the agent

**This spec creates new code, so its new criteria carry witnesses and no
mutants.** The shape check, the tolerance and the strip do not exist yet, so
there is no spelling to pin.

**Every new witness must fail with `events.py` reverted, not merely be missing at
base.** The `revert` gate re-runs each new witness against the reverted source
and blocks any that still pass. All four new criteria describe something base
code gets wrong, so an honest test fails reverted. Import new names inside
tests, not at module scope. A module-scope import of a name you add makes the
reverted run a collection error, which `revert` reads as `skip`.

**`SA-0068` lands first and may add a field to `Agent`.** This spec is stacked
on it. Your shape check must accept whatever field it added, at its annotated
type.

**"Wrong shape" is about JSON types, and JSON is looser than Python.**
- A `float` field accepts an integer: JSON does not preserve the distinction,
  and a hand-written log carries `1` where the writer wrote `1.0`.
- An `int` field accepts only integers. `bool` is a subclass of `int` in
  Python, so check that neither an `int` field nor a `float` field accepts
  `True`.
- `tuple[str, ...]` fields arrive as lists and are coerced today. Keep that
  coercion, and check each element's type.
- The module uses `from __future__ import annotations`, so `int | None`
  resolves to a `types.UnionType`, not a `typing.Union`. Handle both.

Read the existing round-trip tests before writing the check.

**Tolerate, don't reject, in `describe`.** `_when` returns `"unknown"` for
anything it cannot turn into a time. A `Baseline` whose lists differ in length
renders what it can rather than raising. Both are values, not shapes, so
`read_log` does not refuse them.

**Strip what the cell authored, not what `describe` authored.** `Baseline`'s
branch joins two lines with a newline of its own, deliberately, and
`test_describe_renders_every_kind_and_variant` pins it. Applying the strip to
`describe`'s whole return value would remove that newline. The strip belongs
where cell-authored content enters a line: the agent-payload branches and the
raw quarantined line.
