---
id: SA-0070
title: the single renderer raises on a wrong-typed field and prints a cell's control bytes to the operator's terminal
type: bug
priority: 2
depends_on: []
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
      `describe` renders every event `read_log` can return from a corrupt log
      without raising. Its contract is "any `Event`", or it is not the single
      renderer the repo relies on, and every caller would need `watch.py`'s
      guard repeated.
    witness: tests/test_events.py::test_describe_renders_whatever_read_log_returns_from_a_corrupt_log
  - claim: >-
      Every branch that renders an agent payload is clipped. The `text` and
      `tool_use` branches already clip at 160 and 120. The `error`,
      `rate_limit` and fallback branches clip nothing, so a five-thousand-
      character error from a cell reaches the terminal whole.
    witness: tests/test_events.py::test_every_agent_payload_branch_is_clipped
  - claim: >-
      No C0 control character from a cell-authored payload reaches the rendered
      line. An error event carrying an escape sequence currently clears the
      operator's screen and retitles their terminal, and `saffron watch` can
      replay that into a fresh terminal long after the run. The strip happens
      once, in the renderer, not in each caller.
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
      What an attended run prints is unchanged, line for line.
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

**Item 63:** `_describe_agent_event` clips `text` at 160 and `tool_use` at 120,
and its `error`, `rate_limit` and fallback branches clip and strip nothing. An
`Agent` event carrying `{"type": "error", "error": "\x1b[2J\x1b]0;…\x07" +
"A"*5000}` renders with the escape bytes intact. The content is authored inside
a cell, and a cell is untrusted.

## Problem

Two properties the repo assumes of its renderer are not true: that it cannot
raise, and that what it prints is bounded and inert. The first takes down a
caller on a corrupt line. The second hands an untrusted cell the operator's
terminal.

## Out of scope

**`watch.py`'s own guard.** `_is_malformed` becomes redundant once `read_log`
refuses the shape. Leave it: `saffron/watch.py` is forbidden, and a redundant
guard is not a defect.

**C1 controls and full ANSI parsing.** The item asks for C0. A sequence
introduced by a C1 byte is a real but narrower case. File it in your notes if
you think it matters. Do not widen this spec to cover it.

**Checking a `Literal` field's membership.** A `TerminalReason` that is a string
but not one of the five is the right shape carrying an unknown value. `describe`
already has a fallback for it, and a newer Saffron adding a value is the
forward-compatibility case `read_log` exists to allow.

**The golden fixture.** `tests/fixtures/**` is forbidden. If a change here moves
a line the fixture captured, the change is wrong, not the fixture.

## Notes for the agent

**This spec creates new code, so its new criteria carry witnesses and no
mutants.** The shape check and the strip do not exist yet, so there is no
spelling to pin.

**"Wrong shape" is about JSON types, and JSON is looser than Python.** A field
declared `float` that arrives as an integer is the right shape: JSON does not
preserve the distinction, and a hand-written log will carry `1` where the
writer wrote `1.0`. `bool` is a subclass of `int` in Python, so check that a
`bool` field does not accept `1` and a `float` field does not accept `True`.
`tuple[str, ...]` fields arrive as lists and are coerced today, so that coercion
must keep working. Read the existing round-trip tests before writing the check.

**Strip what the cell authored, not what `describe` authored.** `Baseline`'s
branch joins two lines with a newline of its own, deliberately, and the golden
fixture captures it. Applying the strip to `describe`'s whole return value
would remove that newline. The strip belongs where cell-authored content enters
a line: the agent-payload branches and the raw quarantined line.
