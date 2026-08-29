---
id: SA-0017
title: an operator has no way to see what a batch would run before it runs
type: feature
priority: 1
depends_on:
  - SA-0016
touches:
  - saffron/cli.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 6
max_attempts: 3
max_turns: 60
risk: elevated
---

## Context
Last of `SA-0009`'s four-way resplit (`SA-0014`'s Context has the full
history — 990 lines, `EXHAUSTED`, `docs/BACKLOG.md` item 25). `SA-0016`
finished `saffron/scheduler.py`'s `build_queue`. This spec wires it to a
command an operator can actually run: `saffron queue`, which §10 already
declares and which the split's own rationale (`SA-0009`) names as this
half's reader — "how an operator checks tonight's queue before trusting a
night to it."

## Problem
`saffron cell` takes one spec path on the command line; nothing prints what
a whole batch would do. An operator who wants to know what tonight's run
would attempt has no command to ask.

## Acceptance criteria
- [ ] `saffron queue --repo .` prints the queue and the refusals and exits
      `0`; `2` when the repo cannot be read
- [ ] A test asserts that `saffron queue` writes nothing at all — no
      `repos` row, no task row, no state change, no `ORPHANED` stamp —
      against a ledger the repo has never been seen in

## Out of scope
**Nothing runs a cell and nothing writes to the ledger.** No `batches`
table, no `runs.batch_id`, no loop, no stop conditions, no breaker, no
`saffron batch` — that is the second half of §4.2.1 and a separate spec.
`saffron/phases/**`, `saffron/cell/**` and `saffron/report/**` are
forbidden.

## Notes for the agent
**The specs come from `base_sha`, not the working copy.** `DESIGN.md`
§4.2.1: resolve the mirror and `base_sha` the same way `_run_cell` does,
then export `.saffron/specs` at that sha with
`mirror.export_saffron_dir` — it exports the whole `.saffron/`, so `specs/`
arrives with the gates. Hand that directory to `SA-0014`'s
`discover_specs`, and the repo id to `SA-0016`'s `build_queue` via
`ledger.resolve_repo_id` — never `upsert_repo`.

**A test that constructs the value it then asserts on proves nothing about
the caller.** The `saffron queue` test belongs at the CLI, with the queue
arriving from `saffron/scheduler.py` rather than being handed in — the
defect that shipped `SA-0005` green (item 18) and the one the critic caught
in `SA-0007`.

Commit after each coherent step. Uncommitted work dies with the cell.
