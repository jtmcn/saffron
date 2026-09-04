---
id: SA-0040
title: the vocabulary has no renderer, and nothing has checked that nine kinds carry sixty-four lines
type: feature
priority: 1
depends_on:
  - SA-0029
touches:
  - saffron/events.py
  - tests/test_events.py
  - tests/test_session.py
  - tests/fixtures/watch-golden.txt
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/preflight.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - images/**
budget_usd: 12
max_attempts: 3
max_turns: 110
risk: standard
---

## Context
`SA-0029` shipped `saffron/events.py` — nine frozen dataclasses, the `Event`
union, `EventLog` and `read_log`, with the wire format pinned by a test.
Nothing renders one, and nothing emits one.

`SA-0030` and `SA-0031` migrate 64 `watch(...)` call sites onto that
vocabulary, and their single real acceptance criterion is that **the terminal
output does not change**. Both of the things that criterion needs are missing:
a `describe` that turns an event back into the line its call site printed, and
a recorded copy of what those lines are today.

This spec is the second half of a split. The first cut of `SA-0029` carried
both halves and the plan checkpoint rejected it at $2.20 — 1100 estimated lines
against a `feature` ceiling of 600 (§5.4).

## Problem
- **Nine kinds have to carry sixty-four lines and nobody has checked that they
  can.** Roughly thirty of the 64 map to no kind by name — `SCOPE:`, `PLAN:`,
  `SALVAGE:`, `REPAIR:`, `PACKAGE:`, `unstacked:`, `rate limit:`, the
  `{outcome}: $N spent` line — and `PhaseStart` has no call site of its own at
  all. If the vocabulary is short, `SA-0030` discovers it against a blocking
  gate, and its own `## Out of scope` forbids it to add a tenth kind.
- **The current output has no recorded shape**, so a migration that changes it
  by accident cannot be caught. The fixture is what `SA-0030` and `SA-0031`
  assert against, and it must be captured **before** either of them edits a
  call site.
- **Two `describe` implementations are about to exist.** `implement._describe`
  renders the cell's events today; `SA-0031` collapses it into this one. Write
  this so it can be collapsed *into*, not left beside.

## Acceptance criteria
- [ ] `describe(event)` returns the exact line today's `watch` call site would
      have printed, for every kind and every variant
- [ ] **The nine kinds are proven sufficient for all 64 call sites.** A table
      in the module maps every call-site family to the kind that carries it —
      `SCOPE:`, `PLAN:`, `IMPLEMENT:`, `SALVAGE:`, `REPAIR:`, `REVIEW:`,
      `REBUT:`, `PACKAGE:`, `gates:`, `budget:`, `cell:`, `preflight:`,
      `baseline:`, `teardown:`, `agent:`, `rate limit:`, `unstacked:`, and the
      `{outcome}: $N spent, session …` line — and a test asserts every family
      in the table has a kind and renders. **A family that genuinely cannot be
      typed is a finding for the pull request body naming the line**, not a
      free-text escape hatch added quietly: a `message: str` field is the prose
      this vocabulary exists to remove, wearing a dataclass
- [ ] **`tests/fixtures/watch-golden.txt` is asserted, not merely committed.**
      A test drives `run_one_cell` and asserts its printed lines equal the
      fixture, line for line. A criterion satisfied by a committed text file
      cannot tell a capture from a file an agent typed out by reading the
      supervisor; a criterion satisfied by a passing test can, because the
      fixture has to be *reproduced*
- [ ] **The fixture is normalised, or it cannot pass twice.** Captured raw it
      embeds the host's LAN address (from `preflight.probe_addresses`, which
      the session tests do not stub), pytest's absolute `tmp_path` in the
      teardown export line, and a system-prompt character count that moves
      whenever `CONTEXT.md` does. One normaliser replaces each with a stable
      placeholder, the capture and the assertion both go through it, and a test
      asserts it leaves everything else untouched. **This is not hypothetical:
      the cell you are running in has a different LAN address and a different
      `tmp_path` from the host that will run `make check` on your branch.**
- [ ] **The fixture's coverage is stated where it is used, because it is
      partial.** The driven harness monkeypatches the agent, so no `agent:`
      line appears in it, and a green run reaches no `Budget`, no no-commit
      `Terminal`, no failing gate and no PACKAGE line. Capture the green path
      plus at least one failing path, and record in a comment which kinds the
      fixture does **not** cover — `SA-0030` and `SA-0031` are specified to
      trust it and must know what it does not prove
- [ ] The fixture is captured from code **no call site has been changed in**:
      this spec edits no `watch(...)` line, which is what makes the capture
      evidence rather than a restatement
- [ ] Every new test runs with no network and no cell, and **none of them
      carries the `cell` marker**: `pyproject`'s `addopts = "-m 'not cell'"`
      excludes those from the default run, and a golden assertion that is
      skipped is how `SA-0030` and `SA-0031` come to verify their migrations
      against a test that never executes

## Out of scope
**Every call site.** `saffron/cell/**` and `saffron/phases/**` are `forbidden`.
`SA-0030` and `SA-0031` migrate them, and this spec's fixture is only evidence
because it changes none of them.

**`implement._describe`.** It stays where it is until `SA-0031` collapses it.
Deleting it here would change the cell's own output while claiming to record
it.

**Any page.** `saffron/report/**` is `forbidden`. That is `SA-0036`.

**New event kinds.** `SA-0029` fixed the vocabulary at nine. If the mapping
table cannot be completed with nine, that is a finding for the pull request
body — the most useful thing this spec can produce — and a tenth dataclass is
the next spec's, not a repair turn's.

**Changing any message.** If a line reads badly it still reads exactly that way
after this spec. Improving copy in the diff that records the copy makes the
record worthless.

## Notes for the agent
**You have 600 changed lines, tests included.** The `size` gate's `feature`
ceiling is §5.4's and the plan checkpoint tests your estimate against it before
you edit anything. This spec exists because its predecessor planned 1100.
Parametrise: one table-driven test over the mapping table is worth eighteen
near-identical functions asserting the same property.

**A driven cell needs no container, and the fixture test must not be marked
`cell`.** `tests/test_session.py` carries no `pytest.mark.cell`: it drives
`run_one_cell` end to end against a stubbed runtime, a stubbed export and a
monkeypatched `run_agent`, and that is where the capture comes from. The five
genuinely cell-marked files are `test_agent_runner`, `test_image`,
`test_package_cell`, `test_proxy` and `test_worktree`; nothing new joins them.

**`tests/test_session.py` is in `touches` only so the harness can be reached.**
The driving helpers are module-private. Prefer importing them into
`tests/test_events.py` over copying two hundred lines of stubs; edit that file
only if a helper has to be made importable, and change no assertion in it.

**The mapping table is the criterion that protects `SA-0030`.** Nine kinds and
sixty-four lines is not obviously a fit. Completing the table is the work; a
`message: str` that absorbs the awkward ones would pass every test here and
hand `SA-0030` a vocabulary that records nothing.

**Cite code by file and symbol, never by line number.** The design document
says so, and an earlier cut of the companion spec was refused at gate 0 three
times over for ignoring it — gate 0 reports only the first bad citation.

**`implement._describe` is the shape to write toward** — it takes the cell's
event `dict` and returns one line. `SA-0031` collapses it into this function,
so a `describe` that cannot serve its cases forces that spec to keep both.
Note that `review` defines a *second, unrelated* `_describe` taking a
`LensReview`; it has nothing to do with events and is nobody's to move.

Commit after each coherent step. Uncommitted work dies with the cell.
