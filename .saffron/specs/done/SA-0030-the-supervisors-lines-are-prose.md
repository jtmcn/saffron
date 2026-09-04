---
id: SA-0030
title: the supervisor's forty-seven progress lines are prose, and the record needs events
type: refactor
priority: 1
depends_on:
  - SA-0040
  - SA-0029
touches:
  - saffron/cell/session.py
  - tests/test_session.py
  - tests/test_events.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - tests/fixtures/watch-golden.txt
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - images/**
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
`SA-0029` shipped `saffron/events.py` — the vocabulary, `EventLog` and
`read_log`. `SA-0040` shipped `describe`, the `FAMILIES` table mapping every
call-site family to the kind that carries it, and
`tests/fixtures/watch-golden.txt`: the terminal output of a driven session,
captured from code in which no call site had been changed. Nothing emits an
event.

`saffron/cell/session.py` is **1495 lines** and holds **47** `watch(...)` call
sites, re-measured 2026-09-01: preflight's proxy and image lines, the baseline
summary, the plan checkpoint, per-attempt gate decisions, the budget stop,
`SA-0028`'s `SALVAGE:` lines, teardown's patch export, and the terminal line.
It also passes `watch=watch` into the phases at **11** keyword sites, which
`SA-0031` migrates and this spec must leave working.

## Problem
- **The supervisor is where the sequence is decided and where it is lost.**
  Every phase transition, every attempt decision and the budget stop pass
  through here as a string.
- **`emit` has no producer.** `SA-0029` and `SA-0040` built a vocabulary and a
  renderer with no caller; the seam is unproven until a real driver uses it.
- **The default lives in the wrong place to be changed later.** `run_one_cell`
  is where `watch` is defaulted, and `cli.py` never names it. That is what
  keeps this whole change out of `SA-0026`'s file, and it is only true while
  the default stays here.

## Acceptance criteria
- [ ] Every `watch(...)` in `saffron/cell/session.py` is an `emit(<Event>)`,
      and no signature in the file still carries a `watch` parameter
- [ ] **The terminal output does not change.** A test drives a session and
      asserts its printed lines equal `tests/fixtures/watch-golden.txt`, line
      for line
- [ ] **The fixture itself is `forbidden` and the assertion against it is not
      weakened.** In `tests/test_events.py`,
      `test_watch_output_matches_the_golden_fixture` still byte-compares a
      driven run against the whole file, and
      `test_the_join_covers_every_captured_line_a_kind_renders` still passes.
      The *harness* moves and the *recording* does not: the golden test drives
      `run_one_cell` through `tests/test_session.py`'s `_drive` and
      `_stub_the_runtime`, which pass `watch=` today, so those helpers must be
      migrated. Their captured lines are what must come out identical
- [ ] `saffron/cli.py` is not modified and is not in `touches`: the default
      `emit` is constructed inside `session.py`, and a test calls
      `run_one_cell` with no `emit` argument and asserts it still prints
- [ ] The default `emit` fans out to both consumers — the terminal renderer and
      an `EventLog` at `task_dir` — and a test asserts a driven session leaves
      an `events.jsonl` whose `read_log` returns the same sequence the terminal
      printed
- [ ] A gate result event carries `error` distinctly from `fail`, and a test
      drives an attempt where a gate errors and asserts the recorded status
- [ ] An `EventLog` failure does not abort a run: a test makes `task_dir`
      unwritable and asserts the session still reaches its terminal state
- [ ] `phases/` is untouched — it still receives a `watch`-shaped callable, and
      a test asserts the seam between them is intact until `SA-0031`
- [ ] Every new test runs with no network and no cell. **The golden-output
      test in particular must not carry the `cell` marker**: `pyproject`'s
      `addopts` excludes those from the default run, and a skipped assertion is
      how this spec's one real acceptance criterion passes without executing.
      `tests/test_session.py` drives `run_one_cell` against a stubbed runtime
      today and has no `cell` marker anywhere — follow it

## Out of scope
**The phases.** `saffron/phases/**` is `forbidden`. `SA-0031` migrates them,
and doing both here is one diff too wide for one repair loop (item 25).

**Changing any message.** If a line reads badly, it still reads exactly that
way after this spec. The golden fixture is the point; improving copy in the
same diff makes it impossible to tell a migration bug from an edit.

**Any renderer, and any new event kind.** `SA-0029` fixed the vocabulary and
`SA-0040` proved it covers all 64 call sites. A call site that does not fit an
existing kind is a finding for the pull request body, not a tenth dataclass
added here — `events.FINDINGS` already names the two shapes that resisted.

## Notes for the agent
**The golden fixture is the acceptance criterion, not a convenience.** If it
does not match, the migration is wrong — do not regenerate it. It is
`forbidden` here, so an attempt to edit it fails a gate rather than merely
breaking a rule: `SA-0024` made `forbidden` checked against the diff. It was
captured in `SA-0040` from code in which no call site had been changed, which
is the only capture that proves anything.

**`events.FAMILIES` is your map.** `SA-0040` mapped all 64 call-site families
to the nine kinds and asserted every citation resolves. The 47 sites here are
the rows citing `cell/session.py`. If one does not fit its row, that is a
finding, not a reason to widen a kind — `saffron/events.py` is `forbidden`.

**Keep the `emit` default in `session.py`.** `cli.py` is `forbidden` here, and
`run_one_cell` must stay callable with no `emit` argument for every direct
caller and test. `SA-0031` additionally *hoists* a fan-out into `cli.py` so
PACKAGE shares one log; that does not remove this default, and building it here
is what makes this spec landable alone.

**`phases/` still takes a `watch`.** Adapt at the boundary — the phase call
sites keep receiving a string-taking callable until `SA-0031`. A half-migrated
seam that leaves both files broken is the failure this split exists to avoid.

**Six test files outside this spec's `touches` call a phase function with
`watch=`** — `test_implement.py` (21 sites), `test_package.py` (7),
`test_package_cell.py` (2), `test_rebut.py` (1), `test_review.py` (1),
`test_agent_runner.py` (1), re-measured 2026-09-01 — and the adapter is the
only thing keeping them green. That is what makes this spec's scope sufficient
and `SA-0031`'s wider: `tests` is a blocking gate, and a migration that cannot
edit its callers' tests cannot pass. Do not remove the adapter here to be tidy.

**`error` ≠ `fail`, and the events must not blur them.** `fail` means the
repo's code is wrong; `error` means the gate broke, aborts the attempt, and is
charged to nobody.

Commit after each coherent step. Uncommitted work dies with the cell.
