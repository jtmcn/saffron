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
budget_usd: 14
max_attempts: 3
max_turns: 130
risk: standard
---

## Context
`run_one_cell` takes `watch: Callable[[str], None] = print`, and **64 call
sites** author prose into it — `gates: attempt 2, 3 new failures -> repair`,
`budget: $4.20 of $9.00 — stopping`. Measured 2026-09-01: `cell/session.py` 47,
`phases/package.py` 8, `phases/implement.py` 5, `phases/rebut.py` 1,
`phases/review.py` 1, `cli.py` 2. The structure behind each line lives in an
f-string and is gone when the terminal scrolls.

The repo already does this correctly one level down: `agent_runner` emits
Saffron's own typed events as JSON lines and `implement._consume` renders them
with `watch(_describe(event))` — structure first, prose at the edge. Host-side
the arrangement is inverted.

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
- **Nine kinds have to carry sixty-four lines, and nobody has checked that they
  can.** If they cannot, `SA-0030` discovers it against a blocking gate with no
  scope to add a tenth — its own `## Out of scope` forbids exactly that.

## Acceptance criteria
- [ ] `saffron/events.py` defines a frozen dataclass per kind — `Preflight`,
      `Baseline`, `PhaseStart`, `Attempt`, `GateResult`, `Budget`, `Agent`,
      `Terminal`, `Teardown` — each carrying a timestamp and the `spec_id`
      plus its own typed fields, and exports an `Event` union alias naming all
      nine, which is the type `SA-0030`'s `emit` is annotated with
- [ ] **The nine kinds are proven sufficient for all 64 call sites.** A table
      in the module maps every call-site family to the kind that carries it —
      `SCOPE:`, `PLAN:`, `IMPLEMENT:`, `SALVAGE:`, `REPAIR:`, `REVIEW:`,
      `REBUT:`, `PACKAGE:`, `gates:`, `budget:`, `cell:`, `preflight:`,
      `baseline:`, `teardown:`, `agent:`, `rate limit:`, `unstacked:`, and the
      `{outcome}: $N spent, session …` line — and a test asserts every family
      in the table has a kind and renders. Roughly thirty of the sixty-four do
      not map to a kind by name; they are phase-scoped progress and
      `PhaseStart` is what carries them, with the phase and the fact typed
      rather than concatenated into a message. **A family that genuinely
      cannot be typed is a finding for the pull request body naming the line**
      — not a free-text escape hatch added quietly, which would reintroduce
      exactly the prose this spec removes
- [ ] `GateResult` carries all four statuses (`pass`, `fail`, `skip`, `error`)
      and a test asserts `error` and `fail` are distinguishable after a
      round-trip: `error` means the gate broke and is charged to nobody
- [ ] **`Budget` names which of the three ceilings stopped a run**, as a typed
      field over an enumeration and not a free string. The three are
      `budget_usd`, `max_attempts` and `max_turns`, and `SA-0005` is why: it
      died at the turn ceiling with 56% of its budget unspent, and nothing said
      which of the three had stopped it. A test asserts each round-trips
      distinctly
- [ ] **`Terminal` distinguishes the five ways an implement turn can end with
      no commits**, because the supervisor separates five and a boolean would
      re-collapse them: cut off at the turn ceiling with no budget left to
      attempt a salvage; cut off, salvage attempted, nothing recovered; ended
      without finishing and produced nothing (the branch that also carries
      `subtype` and `terminal_reason` — an idle or wall-clock bound, a provider
      wall, a crash); finished on its own and produced nothing; and the plan
      turn's own rejection. A test asserts all five are distinguishable after a
      round-trip. **Cut off and *recovered* is not one of them** — that branch
      has commits and the run continues, so it belongs to `Attempt`
- [ ] `EventLog(task_dir)` appends exactly one JSON object per line to
      `events.jsonl` and flushes per event, so a cell killed mid-run keeps
      everything written before the kill
- [ ] **The on-disk shape is pinned by a test, because three later specs read
      it**: each line carries a `kind` discriminator naming its dataclass, a
      timestamp in one documented representation, and the `spec_id`. A test
      asserts a hand-written line of that shape loads, so the format is fixed
      by the test rather than by whatever the writer happens to emit
- [ ] `read_log` drops a truncated **final** line and returns every whole line
      before it — a test writes a file ending mid-object and asserts the
      earlier events survive. Per-line tolerance, never a whole-file discard,
      the rule `_existing_queue_rows` already applies and names in a
      `ponytail:`
- [ ] `read_log` tolerates an unknown event kind rather than raising, so a log
      written by a newer Saffron stays readable
- [ ] **`Agent` represents all five of its call sites, not only the parsed
      ones.** Two are `agent: (raw)` — a line that was not an event, from a
      process sharing the runner's stdout inside an untrusted cell — and two
      are host-authored (`reaped the cell after the kill`; `result seen, then a
      child held stdout open`). A field holding only a cell event dict cannot
      carry any of the four. A test asserts a raw line round-trips **still
      marked as raw**: the quarantine is the point, and it must survive the
      log, not just the terminal
- [ ] `Agent` carries a parsed cell event dict **verbatim** under one key, and
      no Agent SDK type is imported: `agent_runner` stays the only file that
      has ever seen one
- [ ] `describe(event)` returns the exact line today's `watch` call site would
      have printed, for every kind and every variant in the mapping table
- [ ] **`tests/fixtures/watch-golden.txt` is asserted, not merely committed.**
      A test in `tests/test_events.py` drives `run_one_cell` and asserts its
      printed lines equal the fixture, line for line. A criterion satisfied by
      a committed text file cannot tell a capture from a file an agent typed
      out by reading the supervisor; a criterion satisfied by a passing test
      can, because the fixture has to be *reproduced*
- [ ] **The fixture is normalised, or it cannot pass twice.** Captured raw it
      embeds the host's LAN address (from `preflight.probe_addresses`, which
      the session tests do not stub), pytest's absolute `tmp_path` in the
      teardown export line, and a system-prompt character count that moves
      whenever `CONTEXT.md` does. A single normaliser replaces each with a
      stable placeholder, the capture and the assertion both go through it, and
      a test asserts the normaliser leaves everything else untouched
- [ ] **The fixture's coverage is stated where it is used, because it is
      partial.** The driven harness monkeypatches the agent, so no `agent:`
      line appears in it, and a green run reaches no `Budget`, no no-commit
      `Terminal`, no failing gate and no PACKAGE line. Capture the green path
      plus at least one failing path, and record in a comment which kinds the
      fixture does **not** cover — `SA-0030` and `SA-0031` are specified to
      trust it and must know what it does not prove
- [ ] An `EventLog` write failure raises nothing to its caller — a test points
      it at an unwritable path and asserts the call returns
- [ ] A `ponytail:` names the ceiling: one file per task, no rotation, tens of
      MB a night by §4.1's estimate
- [ ] `docs/BACKLOG.md` records that the event schema wants its own subsection
      under §4 and that adding it is by hand, since `DESIGN.md` is `protected`
      and no cell can write one
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

**Editing the supervisor's tests beyond what the capture needs.**
`tests/test_session.py` is in `touches` for one reason — see the notes — and a
spec that changes no call site has no business changing what those tests
assert.

## Notes for the agent
**Cite code by file and symbol, never by line number.** The design document
says so, and this spec was refused at gate 0 once for ignoring it: a criterion
citing `report/index.py:274` yields the path token `report/index.py`, which
matches no `touches` pattern and — because the `saffron/` prefix is missing —
is not absorbed by the `forbidden` entry either. Two more citations were
queued behind it. Gate 0 reports only the first.

**The golden fixture must be captured from unmodified code.** A fixture
generated after a change proves the change agrees with itself. This spec
changes no call site, which is what makes the capture trustworthy — and it is
the reason this spec exists separately at all.

**A driven cell needs no container, and the fixture test must not be marked
`cell`.** `tests/test_session.py` carries **no** `pytest.mark.cell`: it drives
`run_one_cell` end to end against a stubbed runtime, a stubbed export and a
monkeypatched `run_agent`, and that is where the capture comes from.
`pyproject`'s `addopts = "-m 'not cell'"` excludes `cell`-marked tests from the
default run, so a golden assertion carrying that marker would be **skipped by
`make check`** and `SA-0030` and `SA-0031` would then verify their migrations
against a test that never executes. Capture and assert host-side, unmarked. The
five genuinely cell-marked files are `test_agent_runner`, `test_image`,
`test_package_cell`, `test_proxy` and `test_worktree`; nothing new joins them.

**`tests/test_session.py` is in `touches` only so the harness can be reached.**
The driving helpers are module-private. Prefer importing them into
`tests/test_events.py` over copying two hundred lines of stubs; edit that file
only if a helper has to be made importable, and change no assertion in it.

**Model `SA-0028`'s new facts as typed fields — and there are more of them
than a first read suggests.** The no-commit branch separates *five* endings and
the code says so in as many words: *"Saying 'finished' here would collapse a
third fact into the two this spec exists to separate."* A `cut_off: bool`
re-collapses exactly what `SA-0028` was written to pull apart. The same applies
to the ceiling: "which of the three stopped this" is an enumeration over
`budget_usd` / `max_attempts` / `max_turns`, not a sentence. These arrive as
prose today; do not enshrine them that way.

**The mapping table is the criterion that protects `SA-0030`.** Nine kinds and
sixty-four lines is not obviously a fit, and the two specs downstream may not
add a tenth kind. If the table cannot be completed, saying so in the pull
request body — with the lines that resist — is a correct and useful outcome.
Inventing a `message: str` field to absorb them is not: that is the prose this
spec exists to remove, wearing a dataclass.

**`_describe` already exists in `implement`** (taking an event `dict`) for the
cell's own events. `SA-0031` moves it. Write `describe` here so that the moved
one can collapse into it, not beside it. Note that `review` defines a *second,
unrelated* `_describe` taking a `LensReview`; it has nothing to do with events
and is nobody's to move.

**A dataclass per kind, not one class with a `type` string.** The cell uses a
dict discriminator because it crosses a process boundary and must never raise
on an unknown shape. The host does not cross one, and a typed field is what
lets a renderer know what it holds. The wire still needs a discriminator, which
is why the on-disk shape is its own criterion: typed in memory, tagged on disk.

Commit after each coherent step. Uncommitted work dies with the cell.
