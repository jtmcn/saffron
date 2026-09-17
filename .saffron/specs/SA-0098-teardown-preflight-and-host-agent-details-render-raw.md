---
id: SA-0098
title: describe prints teardown, preflight and host agent details whole and with their control bytes, and a proxy denial names hosts a cell chose
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
  - tests/fixtures/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/watch.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
acceptance:
  - claim: >-
      Every `Teardown` line that renders a detail renders it with every
      control character replaced by a space, and clipped to the same bound a
      `PhaseStart` detail gets. One of those details is the proxy's denial
      list, which names hosts a cell asked to reach. Today a teardown detail
      is printed whole and with its control bytes.
    witness: tests/test_events.py::test_a_teardown_detail_is_stripped_and_clipped
  - claim: >-
      The same holds for every `Preflight` branch that renders a detail: the
      `cell_up` line, the `unstacked` line, and the general preflight line.
      Today all three print the detail whole and with its control bytes.
    witness: tests/test_events.py::test_a_preflight_detail_is_stripped_and_clipped
  - claim: >-
      An `Agent` event that carries a host `detail` and no cell event renders
      that detail the same way. One such detail quotes the cell runtime's
      stderr when a cell will not reap. Today it is printed whole and with its
      control bytes.
    witness: tests/test_events.py::test_an_agent_detail_is_stripped_and_clipped
  - claim: >-
      Every call-site family still renders the exact line it did, for a
      detail with no control characters that is shorter than the bound.
    witness: tests/test_events.py::test_every_family_has_a_kind_and_renders
    preserves: true
  - claim: >-
      A green run still prints exactly the lines the golden watch fixture
      holds.
    witness: tests/test_events.py::test_watch_output_matches_the_golden_fixture
    preserves: true
  - claim: >-
      A `PhaseStart` or `Terminal` detail is still clipped at the bound, as
      `SA-0084` made it.
    witness: tests/test_events.py::test_a_phase_or_terminal_detail_is_clipped
    preserves: true
---

## Context

Backlog item **63**, the part `SA-0084` (PR #249) deferred.

`describe` (`saffron/events.py:696`) is the one renderer for every event, and
`_clean` (`:634-644`) is where cell-reachable text is made safe for a terminal:
every C0 control character and DEL becomes a space, then the value is clipped.
`SA-0070` routed the `Agent` payload fields through it, and `SA-0084` routed
`PhaseStart.detail` (`:755-756`) and `Terminal`'s details (`:799-821`), clipped
at `_DETAIL_BOUND` (`:649`). Three renders still print a detail raw:

- `Preflight`, all three branches (`:707-712`): `cell: {event.detail}`,
  `unstacked: {event.detail}` and `preflight: {event.detail}`.
- `Teardown` (`:823-826`): `teardown: {event.detail}`.
- `Agent` with no cell event (`:797`): `agent: {event.detail}`.

What reaches those details:

- **Teardown.** `cell_down` reports the proxy's denials as
  `f"proxy DENIED {denied}"` (`saffron/cell/session.py:955`). Those are hosts
  the cell tried to reach, so a cell chooses that text.
  `export_patch`'s failure detail quotes an exception (`session.py:766`).
- **Preflight.** `saffron/task.py:202-208` puts `str(gone)` from a `ParentGone` into
  the `unstacked` detail. `session.py:1317` puts a spec-drift description into
  the general one.
- **Agent.** `saffron/phases/implement.py:295` renders
  `f"the cell would not reap — {reaped.stderr.strip()[:200]}"`, which is the
  cell runtime's stderr.

`_clean`'s docstring (`events.py:640-643`) still says that fields carrying only
host text, `Agent.detail` among them, skip it. After this change that sentence
is false.

## Problem

Text a cell can influence reaches the operator's terminal unstripped through
three event kinds. `saffron watch` can replay it into a fresh terminal long
after the run.

## Out of scope

**Any call site.** The fix lives in `describe`, once, not in each emitter.
That is why `saffron/cell/**`, `saffron/phases/**` and `saffron/task.py` are
forbidden.

**The `teardown` start line.** `step == "start"` renders a fixed word and no
detail.

**`Baseline`, `Attempt`, `Ceilings`, `GateResult`, `Budget`.** They render
host-computed values, not free text.

## Notes for the agent

**This is new code at existing branches, so the criteria carry witnesses and
no mutants.** The spelling of each call is yours. `witness` will report `skip`
for all three, and that is expected.

**Reuse `_clean` and `_DETAIL_BOUND`,** as the `PhaseStart` branch does. A
detail here is host prose around a quoted fragment, the same shape as a phase
detail, so the same bound fits. Correct the `_clean` docstring's sentence about
`Agent.detail` in the same change.

**Cover every branch that renders a detail.** Fixing only the general
`preflight:` line, and not `cell:` and `unstacked:`, is the likeliest wrong
answer. Each witness should drive each branch.

**Check both halves in each witness.** Walk every code point from U+0000 to
U+001F plus U+007F through `describe` itself, and assert that the text around
it survives, as `test_a_phase_line_cannot_put_control_characters_on_a_terminal`
(`tests/test_events.py:1460`) does. Separately, render a detail longer than the
bound and assert the line stops at it, as
`test_a_phase_or_terminal_detail_is_clipped` (`:1525`) does. A render that
strips without clipping, or clips without stripping, must fail its witness.

**Import `_DETAIL_BOUND` inside the test body,** as that test does, and
anything this change adds as well: a module-scope import of a new name turns
`revert`'s reverted run into a collection error, which it reads as `skip`.

**The golden fixture must not move.** Its `preflight:` lines
(`tests/fixtures/watch-golden.txt`) are short and plain, so they render the same either
way. If the fixture changes, the render changed something it should not have.
