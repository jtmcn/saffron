---
id: SA-0084
title: describe prints phase and terminal details whole and with their control bytes, and several quote text a model wrote
type: bug
priority: 3
depends_on: [SA-0080]
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
  - spikes/**
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
  - saffron/replay.py
budget_usd: 5
max_attempts: 3
max_turns: 40
acceptance:
  - claim: >-
      A `PhaseStart` line renders with every control character in its detail
      replaced by a space. Several of those details quote text a model wrote:
      a plan or scope artifact's validation error, a lens report that was not
      the schema, a rebuttal that could not be read. Today an escape sequence
      there reaches the operator's terminal intact, as the agent's own events
      did before `SA-0070`.
    witness: tests/test_events.py::test_a_phase_line_cannot_put_control_characters_on_a_terminal
  - claim: >-
      A `Terminal` line renders its detail the same way. A rejected plan's
      detail is the rejection's own text, which names the paths the plan
      proposed.
    witness: tests/test_events.py::test_a_terminal_line_cannot_put_control_characters_on_a_terminal
  - claim: >-
      Both details are clipped to a bound, so a five-thousand-character
      validation error renders as one bounded line rather than whole.
    witness: tests/test_events.py::test_a_phase_or_terminal_detail_is_clipped
  - claim: >-
      `events.jsonl` still reproduces what the terminal printed, line for
      line, as it does today.
    witness: tests/test_events.py::test_events_jsonl_reproduces_what_the_terminal_printed
    preserves: true
  - claim: >-
      Every line family still renders from its kind, as it does today.
    witness: tests/test_events.py::test_every_family_has_a_kind_and_renders
    preserves: true
---

## Context

`docs/BACKLOG.md` item **63**, the follow-up its status line names. It was
found reviewing `SA-0070` (2026-09-11). `SA-0070` made `_clean` the one place
cell-authored text is made safe for a terminal: every control character becomes
a space, then the text is clipped. It applied `_clean` to the `Agent` event
only.

`describe` renders `PhaseStart` as `{label}: {detail}` and a `Terminal` detail
verbatim. Model-written text reaches those details at these call sites, among
others:

- `plan_checkpoint` re-prompts with `not the schema, re-prompting once — {exc}`
  and `proposal refused, re-prompting once — {exc}`, where `exc` quotes the
  artifact.
- A lens whose report is not the schema is rendered as
  `{lens}: not the schema, re-prompting once — {exc}` (`saffron/phases/review.py`).
- A rebuttal turn that could not be read carries its parse error
  (`saffron/phases/rebut.py`).
- A rejected plan ends the task with `Terminal(reason="plan_rejected",
  detail=str(rejected))`.

`saffron watch` can replay any of these into a fresh terminal long after the
task.

## Problem

The single renderer strips a cell's control bytes from one kind of event and
prints them intact from two others that carry the same kind of text.

## Out of scope

**`Preflight` and `Teardown` details.** Whether cell-written text reaches them
is unmeasured. A proxy denial naming a host the cell asked for is the likeliest
case, and it belongs in the backlog, not here.

**Clipping host-written text for its own sake.** The bound exists because model
text shares the field.

**Any call site.** The fix lives in `describe`, once, not in each caller. That
is why `saffron/cell/**` and `saffron/phases/**` are forbidden.

## Notes for the agent

**This is new code at existing call sites, so the criteria carry witnesses and
no mutants.** The spelling of the call is yours.

**Reuse `_clean`,** as the `Agent` branches do. It replaces newlines too, so a
multi-line validation error becomes one line. That is intended: a terminal line
is one line.

**Pick a bound no line in this suite's fixtures already exceeds,** and say in a
comment what it was chosen against. The two `preserves` witnesses fail if a
real line gets cut. `160`, the `Agent` bound, may be too tight for a host
detail, so check before choosing it.

**Model the witnesses on SA-0070's own:**
`test_an_agent_payload_cannot_put_control_characters_on_a_terminal` walks every
code point from U+0000 to U+001F plus U+007F, and asserts that the content around
them survives. Import `_clean`, or anything else new, inside the test body, as
that test does. A module-scope import of a name you add turns the reverted run
into a collection error, which `revert` reads as `skip`.

**Cover every `Terminal` branch that renders a detail,** not only
`plan_rejected`. `cut_off_no_salvage_room` renders one too.

**This spec is cut from `SA-0080`'s branch**, which edits `read_log` in the same
file.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and `integrity` fails that suppression
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
