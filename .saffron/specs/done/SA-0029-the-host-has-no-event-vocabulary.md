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

**This spec is the types and the log, and nothing that renders them.** A first
cut carried the renderer and its golden fixture too, and the plan checkpoint
rejected it at $2.20: the agent's own estimate was 1100 changed lines against
the 600 a `feature` is allowed (§5.4). `SA-0040` has the other half, and lands
before `SA-0030` migrates anything.

Nothing emits an `Event` when this lands.

## Problem
- **There is no type that can carry a host-side fact.** `SA-0030` and `SA-0031`
  migrate call sites and cannot begin without one.
- **A night's sequence is unrecoverable.** The ledger records outcomes and not
  order. Three task rows in this repo's ledger are `ORPHANED` at `$0.00` — two
  with no attempt row at all and one with a single attempt — a cell that died
  with nothing written. SQL can say a task ended that way; it cannot say how
  far it got first.
- **The facts `SA-0028` just separated are about to be re-collapsed.** It
  shipped, as prose, which of three ceilings stopped a run and which of five
  ways an implement turn ended with nothing committed. A vocabulary that models
  those as strings loses them again at the first migration.

## Acceptance criteria
- [ ] `saffron/events.py` defines a frozen dataclass per kind — `Preflight`,
      `Baseline`, `PhaseStart`, `Attempt`, `GateResult`, `Budget`, `Agent`,
      `Terminal`, `Teardown` — each carrying a timestamp and the `spec_id`
      plus its own typed fields, and exports an `Event` union alias naming all
      nine, which is the type `SA-0030`'s `emit` is annotated with
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
- [ ] **`Agent` represents an unparsed line as well as a parsed one.** Two of
      its five call sites are `agent: (raw)` — a line that was not an event,
      from a process sharing the runner's stdout inside an untrusted cell — and
      two are host-authored, with no cell event behind them at all. A field
      holding only a parsed dict carries none of the four. A test asserts a raw
      line round-trips **still marked as raw**: the quarantine is the point and
      it must survive the log, not live only on the terminal
- [ ] `Agent` carries a parsed cell event dict **verbatim** under one key, and
      no Agent SDK type is imported: `agent_runner` stays the only file that
      has ever seen one
- [ ] `EventLog(task_dir)` appends exactly one JSON object per line to
      `events.jsonl` and flushes per event, so a cell killed mid-run keeps
      everything written before the kill
- [ ] **The on-disk shape is pinned by a test, because four later specs read
      it**: each line carries a `kind` discriminator naming its dataclass, a
      timestamp in one documented representation, and the `spec_id`. A test
      asserts a **hand-written** line of that shape loads, so the format is
      fixed by the test rather than by whatever the writer happens to emit
- [ ] `read_log` drops a truncated **final** line and returns every whole line
      before it — a test writes a file ending mid-object and asserts the
      earlier events survive. Per-line tolerance, never a whole-file discard,
      the rule `_existing_queue_rows` already applies and names in a
      `ponytail:`
- [ ] `read_log` tolerates an unknown event kind rather than raising, so a log
      written by a newer Saffron stays readable
- [ ] An `EventLog` write failure raises nothing to its caller — a test points
      it at an unwritable path and asserts the call returns
- [ ] A `ponytail:` names the ceiling: one file per task, no rotation, tens of
      MB a night by §4.1's estimate
- [ ] `docs/BACKLOG.md` records that the event schema wants its own subsection
      under §4 and that adding it is by hand, since `DESIGN.md` is `protected`
      and no cell can write one
- [ ] Every new test runs with no network and no cell

## Out of scope
**`describe`, and every renderer.** `SA-0040` writes it, together with the
mapping table proving the nine kinds carry all 64 call sites, and the golden
fixture. Writing it here is what made the first cut of this spec 1100 lines.

**The golden fixture.** `SA-0040`. It cannot be captured by a spec that has no
renderer to capture the output of.

**Every call site.** `saffron/cell/**` and `saffron/phases/**` are `forbidden`.
`SA-0030` and `SA-0031` migrate them.

**Any page.** `saffron/report/**` is `forbidden`. That is `SA-0036`.

**Emitting from the scheduler.** It has no `watch` today and gains events when
§4.2's orchestration exists; adding them now is events with no producer.

**Reading the log for a decision.** Nothing consumes `events.jsonl` for
control, here or ever: every control that matters lives outside the cell.

**Rotation, compression or a size cap.** Named as a ceiling, not built.

## Notes for the agent
**You have 600 changed lines, tests included, and the last attempt planned
1100.** The `size` gate's `feature` ceiling is §5.4's, the plan checkpoint
tests your own estimate against it before you edit anything, and this spec was
already re-cut once for exceeding it. **Parametrise.** A table-driven
round-trip over nine kinds is forty lines; nine near-identical test functions
are three hundred, and they assert the same thing.

**Cite code by file and symbol, never by line number.** The design document
says so, and an earlier cut of this spec was refused at gate 0 for ignoring it:
a criterion citing `report/index.py:274` yields the path token
`report/index.py`, which matches no `touches` pattern and — the `saffron/`
prefix being absent — is not absorbed by the `forbidden` entry either. Two more
were queued behind it, and gate 0 reports only the first.

**Model `SA-0028`'s new facts as typed fields — there are more of them than a
first read suggests.** The no-commit branch separates *five* endings and the
code says so in as many words: *"Saying 'finished' here would collapse a third
fact into the two this spec exists to separate."* A `cut_off: bool`
re-collapses exactly what `SA-0028` was written to pull apart. The same applies
to the ceiling: "which of the three stopped this" is an enumeration over
`budget_usd` / `max_attempts` / `max_turns`, not a sentence.

**A dataclass per kind, not one class with a `type` string.** The cell uses a
dict discriminator because it crosses a process boundary and must never raise
on an unknown shape. The host does not cross one, and a typed field is what
lets a renderer know what it holds. The wire still needs a discriminator, which
is why the on-disk shape is its own criterion: typed in memory, tagged on disk.

**Design the fields for `SA-0040`, which has to render every one of the 64
lines from them.** You are not writing that renderer, but a kind whose fields
cannot reproduce its call site's line is a defect this spec ships and the next
one pays for. `PhaseStart` in particular carries roughly thirty phase-scoped
progress lines — `SCOPE:`, `PLAN:`, `IMPLEMENT:`, `SALVAGE:`, `REPAIR:`,
`REVIEW:`, `REBUT:`, `PACKAGE:` — so its fields have to be general enough for
those and typed enough not to be a message string wearing a dataclass.

Commit after each coherent step. Uncommitted work dies with the cell.
