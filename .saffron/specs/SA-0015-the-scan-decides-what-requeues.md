---
id: SA-0015
title: the ledger cannot say which tasks exist per spec, so nothing decides what re-queues
type: feature
priority: 1
depends_on:
  - SA-0014
touches:
  - saffron/ledger.py
  - saffron/scheduler.py
  - tests/test_scheduler.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 10
max_attempts: 4
max_turns: 80
risk: elevated
---

## Context
Second of `SA-0009`'s four-way resplit (`SA-0014`'s Context has the full
history — 990 lines, `EXHAUSTED`, `docs/BACKLOG.md` item 25).
`saffron/scheduler.py` does not exist; §10 declares it. This spec builds the
part that decides *whether* a spec `SA-0014`'s `discover_specs` found is
queued — the `spec_sha`-keyed done/re-queue filter and the ordering — and
refuses only the specs that couldn't parse. `SA-0016` adds the other four of
§4.2.1's six refusals to the same function.

## Problem
- **`saffron/ledger.py` cannot answer "has this spec been attempted?"**
  `queue_lines` reads every task in every repo unfiltered — the morning
  queue's question, not the scheduler's.
- **There is no scan that turns "specs on disk" into "specs worth
  running."** Every call today hands `saffron cell` one path by hand.

## Acceptance criteria
- [ ] `saffron/ledger.py` answers, for one repo, which tasks exist per
      `spec_id` and `spec_sha` with their state, and resolves a repo to its
      id **without inserting one**
- [ ] `saffron/scheduler.py` returns an ordered queue and a list of
      refusals; at this spec, a refusal appears only for a path
      `discover_specs` reported as a parse failure, carrying that path and
      the reason
- [ ] A spec is queued unless a task **at that `spec_sha`** is in a state
      done with it: `READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN`, `MERGED`,
      `MERGE_FAILED`, `REJECTED`, `EXHAUSTED`, `NOT_IMPLEMENTED`,
      `PLAN_REJECTED`, `SCOPE_REVIEW`. `CHANGES_REQUESTED`, `RATE_LIMITED`,
      `GATE_ERROR`, `PREFLIGHT_FAILED` and `ORPHANED` re-queue, and a
      re-queued spec reports the existing `task_id` it would resume rather
      than a new one
- [ ] Candidates are ordered by priority, then by `discover_specs`' filename
      order to break ties
- [ ] Every test in `tests/test_scheduler.py` runs with no network and no
      cell

## Out of scope
**No PR-based refusal, no criteria/`touches` refusal, no `depends_on`
refusal.** `SA-0016` adds all four to the same `build_queue` this spec
builds; nothing here calls `gh`, and `GhRunner` does not appear in this diff.
`saffron queue` and the CLI are `SA-0017` — nothing here is reachable from
the command line yet. `saffron/phases/**`, `saffron/cell/**` and
`saffron/report/**` are forbidden.

## Notes for the agent
**The scan resolves to a task, not to a spec** (`DESIGN.md` §4.2.1): a spec
with a task at this `spec_sha` in a re-queueing state resumes that task row;
a spec with no such task gets `task_id: None`. Minting a fresh candidate per
queued spec looks equivalent and is not — the refusal gate `SA-0016` adds
keys ownership on `task_id`, and a spec-keyed scan would break the one case
`CHANGES_REQUESTED` re-queuing exists for.

**In-flight states are out of scope for this spec.** `DESIGN.md` §4.2.1
stamps a task left in `IMPLEMENTING` as `ORPHANED` before filtering; that is
a write, and it belongs to the half of `SA-0009` that runs a cell, not this
one. Treat an in-flight state as neither done nor re-queueing for now — it
simply isn't one of the two lists above, which is enough to keep this spec
read-only.

`saffron/intake.parse_spec` must keep accepting `depends_on` — `SA-0006` and
`SA-0007` carry it, and it is refused at the gate `SA-0016` builds, not
parsed away.

Commit after each coherent step. Uncommitted work dies with the cell.
