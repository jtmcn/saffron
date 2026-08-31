---
id: SA-0019
title: nothing records whether a task merged, so the ledger's last word is always READY_FOR_REVIEW
type: feature
priority: 1
depends_on: []
touches:
  - saffron/reconcile.py
  - saffron/ledger.py
  - saffron/cli.py
  - tests/test_reconcile.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/scheduler.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/report/**
budget_usd: 12
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
§3.3 draws four arrows out of `READY_FOR_REVIEW` — `APPROVED`, `CHANGES_REQUESTED`,
`REJECTED`, and onward to `MERGE_TRAIN` and `MERGED`. Five of those six states are
in `scheduler.DONE_STATES` and one (`ORPHANED`) is in `REQUEUE_STATES`. **Nothing in
`saffron/` writes any of them.** `set_task_state` is the only writer of
`tasks.state`, and the last thing PACKAGE says is `READY_FOR_REVIEW`.

§6 already measured this against the real ledger and named it: *"nothing anywhere
records whether a task was merged, which is the trailing accept rate's whole
input."*

Measured on this machine, 2026-08-30:

```
uv run python -c "
import sqlite3
db = sqlite3.connect('$HOME/.saffron/ledger.db')
for r in db.execute('select task_id,spec_id,state,pr_url from tasks where pr_url is not null'):
    print(r)"
```

returns six rows, every one `READY_FOR_REVIEW`. `gh pr view` says five of the six
pull requests are `MERGED` — #51, #56, #59, #60, #64, merged between 2026-08-29
and 2026-08-30 — and only #65 is still open. The ledger is wrong about five of
six tasks, and it has no mechanism that could ever make it right.

## Problem
- **The states exist, the filter reads them, and no producer writes them.**
  `DONE_STATES` lists `MERGED`, `APPROVED`, `MERGE_TRAIN`, `MERGE_FAILED` and
  `REJECTED`; `report/index.py` sorts on `ORPHANED`. Every consumer is built
  against a column that stops moving the moment PACKAGE finishes.
- **The decision is made somewhere the host never reads.** §6.1 is explicit —
  *"You approve in GitHub; nothing merges on your click."* GitHub's pull request
  state **is** the operator's decision surface, so the ledger can only learn what
  happened by asking it. Today nobody asks.
- **A corpse is never stamped either.** §4.2.1 requires the scan to stamp any
  in-flight task `ORPHANED` before filtering; `scheduler.py`'s `Candidate`
  docstring defers that write to "the half of `SA-0009` that runs a cell", which
  does not exist. A host power cut leaves a task reading `IMPLEMENTING` forever,
  and `IMPLEMENTING` is on neither list.

## Acceptance criteria
- [ ] A task whose pull request merged is recorded `MERGED`; one whose pull
      request is closed unmerged is `REJECTED`; one still open with changes
      requested is `CHANGES_REQUESTED`; one open and undecided is left exactly
      as it was
- [ ] A `gh` that is missing, unauthenticated, or erroring leaves every task's
      state precisely as it found it, and the command reports how many tasks it
      could not ask about — absence of an answer is never recorded as "not
      merged"
- [ ] Reconciliation never moves a task backwards: a task already `MERGED` stays
      `MERGED` on every subsequent run
- [ ] Every task in an in-flight state (`DRAFT`, `QUEUED`, `DIAGNOSING`,
      `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING`, `REBUTTING`) is
      stamped `ORPHANED`
- [ ] `saffron reconcile --repo .` runs it on demand, and `saffron queue`
      reconciles before it scans, so the scan filters on current state
- [ ] The fixture is this repository's own six recorded tasks and their real
      pull request states — five merged, one open — not a spec written to be
      obviously stale
- [ ] `docs/BACKLOG.md` records that the ledger was wrong about five of six
      tasks, with the measurement above rather than a restatement of it
- [ ] Every new test runs with no network and no cell

## Out of scope
**Merging anything.** §6.1's merge train rebases, re-verifies and merges; this
spec only *observes* what a human already did in GitHub. `saffron/phases/**` is
forbidden. `MERGE_TRAIN` and `MERGE_FAILED` get no producer here.

**The `depends_on` gate.** `saffron/scheduler.py` is forbidden — gate 1 is
`SA-0020`, which depends on this one because a gate that reads task states is
only safe once something keeps them current. `Candidate`'s docstring will be
left describing a deferral this spec has ended; correcting it is `SA-0020`'s,
inside the file it already owns.

**A `merged_at` column and the accept-rate rendering.** `set_task_state` already
stamps `updated_at`, which is the input §6 asks for; `saffron/report/**` is
forbidden. A column added before a reader exists is a column nobody validates.

**Editing any merged spec's text.** An edit moves its `spec_sha`, and a spec
that is done at one sha is queued again at another (§4.2.1). `.saffron/**` is
forbidden.

## Notes for the agent
**The reader/writer asymmetry is the whole defect risk.** `scheduler._open_prs`
returns `[]` on anything that keeps its answer from being trustworthy, and its
docstring calls that deliberate — correct for a *refuser*, which merely declines
to refuse. It is catastrophic for a *writer*: an empty answer would read as "no
open pull request", and stamp `REJECTED` on five healthy branches. Copy the
best-effort shape and invert what it does with the failure.

**`GhRunner` already exists twice** — `scheduler.py` and `phases/package.py` —
duplicated on purpose, each with a note saying why it is not imported from the
other. Follow that, and a test never reaches the network or whoever `gh` happens
to be logged in as.

**Item 18's rule, one spec later.** A fixture you invent proves the happy path
and nothing about the caller. The six rows in this machine's ledger, with their
real `pr_url`s and the states GitHub actually returns, are the fixture — and the
test that would have failed is the one asserting five of them reach `MERGED`
while #65 does not move.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Drive this through `reconcile`, not by handing a state string to
`set_task_state`.

Commit after each coherent step. Uncommitted work dies with the cell.
