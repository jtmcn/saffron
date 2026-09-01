---
id: SA-0029
title: the host has no event vocabulary, so a night's sequence exists only as prose
type: feature
priority: 1
depends_on:
  - SA-0028
touches:
  - saffron/events.py
  - tests/test_events.py
  - tests/fixtures/watch-golden.txt
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - images/**
budget_usd: 10
max_attempts: 3
max_turns: 90
risk: standard
---

## Context
`run_one_cell` takes `watch: Callable[[str], None] = print` (`session.py:583`),
and **64 call sites** author prose into it — `gates: attempt 2, 3 new failures
-> repair`, `budget: $4.20 of $9.00 — stopping`. Measured 2026-09-01:
`cell/session.py` 47, `phases/package.py` 8, `phases/implement.py` 5,
`phases/rebut.py` 1, `phases/review.py` 1, `cli.py` 2. The structure behind
each line lives in an f-string and is gone when the terminal scrolls.

The repo already does this correctly one level down: `images/agent_runner.py`
emits Saffron's own typed events as JSON lines and `phases/implement.py`'s
`_consume` renders them with `watch(_describe(event))` — structure first, prose
at the edge. Host-side the arrangement is inverted.

This spec builds the vocabulary and changes no caller. Nothing emits an `Event`
when it lands.

## Problem
- **There is no type that can carry a host-side fact.** `SA-0030` and `SA-0031`
  migrate call sites and cannot begin without one.
- **A night's sequence is unrecoverable.** The ledger records outcomes and not
  order. Three task rows in this repo's ledger are `ORPHANED` at `$0.00` — two
  with no attempt row at all and one with a single attempt — a cell that died
  with nothing written. SQL can say a task ended that way; it cannot say how
  far it got first.
- **The current output has no recorded shape**, so a migration that changes it
  by accident cannot be caught. The golden fixture here is what later specs
  assert against.

## Acceptance criteria
- [ ] `saffron/events.py` defines a frozen dataclass per kind — `Preflight`,
      `Baseline`, `PhaseStart`, `Attempt`, `GateResult`, `Budget`, `Agent`,
      `Terminal`, `Teardown` — each carrying a timestamp and the `spec_id`
      plus its own typed fields
- [ ] `GateResult` carries all four statuses (`pass`, `fail`, `skip`, `error`)
      and a test asserts `error` and `fail` are distinguishable after a
      round-trip: `error` means the gate broke and is charged to nobody
- [ ] **`Budget` names which of the three ceilings stopped a run**, as a typed
      field over an enumeration and not a free string. The three are
      `budget_usd`, `max_attempts` and `max_turns` (`intake.py:78`–`90`), and
      `SA-0005` is why: it died at the turn ceiling with 56% of its budget
      unspent, and nothing said which of the three had stopped it. A test
      asserts each of the three round-trips distinctly
- [ ] **`Terminal` distinguishes at least four ways a turn can end with no
      commits**, because `session.py:1095`–`1201` separates four and a boolean
      would re-collapse them: cut off at the turn ceiling and salvaged; cut off
      and could not be salvaged; ended without finishing and produced nothing
      (an idle or wall-clock bound, a provider wall, a crash — the branch that
      also carries `subtype` and `terminal_reason`); and finished on its own
      and produced nothing. A test asserts all four are distinguishable after a
      round-trip
- [ ] `EventLog(task_dir)` appends exactly one JSON object per line to
      `events.jsonl` and flushes per event, so a cell killed mid-run keeps
      everything written before the kill
- [ ] `read_log` drops a truncated **final** line and returns every whole line
      before it — a test writes a file ending mid-object and asserts the
      earlier events survive. Per-line tolerance, never a whole-file discard,
      the rule `_existing_queue_rows` already applies and names in a
      `ponytail:` (`report/index.py:274`)
- [ ] `read_log` tolerates an unknown event kind rather than raising, so a log
      written by a newer Saffron stays readable
- [ ] `Agent` carries a cell event dict **verbatim** under one key, and no
      Agent SDK type is imported: `images/agent_runner.py` stays the only file
      that has ever seen one
- [ ] `describe(event)` returns the exact line today's `watch` call site would
      have printed, for every kind
- [ ] `tests/fixtures/watch-golden.txt` records the current terminal output of
      a driven session, captured from **unmodified** code and committed here as
      the fixture `SA-0030` and `SA-0031` assert against
- [ ] An `EventLog` write failure raises nothing to its caller — a test points
      it at an unwritable path and asserts the call returns
- [ ] A `ponytail:` names the ceiling: one file per task, no rotation, tens of
      MB a night by §4.1's estimate
- [ ] Every new test runs with no network and no cell

## Out of scope
**Every call site.** `saffron/cell/**` and `saffron/phases/**` are `forbidden`
here. `SA-0030` and `SA-0031` migrate them.

**Any renderer.** `saffron/report/**` is `forbidden`. The page is `SA-0036`.

**Emitting from the scheduler.** It has no `watch` today and gains events when
§4.2's orchestration exists; adding them now is events with no producer.

**Reading the log for a decision.** Nothing consumes `events.jsonl` for
control, here or ever: every control that matters lives outside the cell.

**Rotation, compression or a size cap.** Named as a ceiling, not built.

## Notes for the agent
**The golden fixture must be captured from unmodified code.** A fixture
generated after a change proves the change agrees with itself. This spec
changes no call site, which is what makes the capture trustworthy — and it is
the reason this spec exists separately at all.

**A "driven session" needs no container, and the fixture test must not be
marked `cell`.** `tests/test_session.py` carries **no** `pytest.mark.cell`: it
drives `run_one_cell` end to end against a stubbed runtime, a stubbed export
and a monkeypatched `run_agent`, and that is where the capture comes from.
`pyproject`'s `addopts = "-m 'not cell'"` excludes `cell`-marked tests from the
default run, so a golden assertion carrying that marker would be **skipped by
`make check`** and `SA-0030` and `SA-0031` would then verify their migrations
against a test that never executes. Capture and assert host-side, unmarked.
The five genuinely cell-marked files are `test_agent_runner.py`, `test_image.py`,
`test_package_cell.py`, `test_proxy.py` and `test_worktree.py`; nothing new
joins them.

**Model `SA-0028`'s new facts as typed fields, not as strings inside a
message — and there are more of them than a first read suggests.** The
`commits == 0` branch in `session.py` separates **four** endings, not two, and
the code says so in as many words: *"Saying 'finished' here would collapse a
third fact into the two this spec exists to separate."* A `cut_off: bool`
re-collapses exactly what `SA-0028` was written to pull apart. The same applies
to the ceiling: "which of the three stopped this" is an enumeration over
`budget_usd` / `max_attempts` / `max_turns`, not a sentence. These arrive as
prose today; do not enshrine them that way.

**`_describe` already exists in `phases/implement.py`** (line 182, taking an
event `dict`) for the cell's own events. `SA-0031` moves it. Write `describe`
here so that the moved one can collapse into it, not beside it. Note that
`phases/review.py:216` defines a *second, unrelated* `_describe` taking a
`LensReview`; it has nothing to do with events and is nobody's to move.

**A dataclass per kind, not one class with a `type` string.** The cell uses a
dict discriminator because it crosses a process boundary and must never raise
on an unknown shape. The host does not cross one, and a typed field is what
lets a renderer know what it holds.

Commit after each coherent step. Uncommitted work dies with the cell.
