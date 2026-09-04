---
id: SA-0045
title: a batch has no row, and a task cannot say which policy it ran under
type: feature
priority: 1
depends_on: []
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - tests/test_ledger.py
  - tests/test_session.py
  - tests/test_package.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
budget_usd: 10
max_attempts: 3
max_turns: 80
risk: elevated
---

## Context

§4.2.1 names the schema a batch needs, and says why it is not the same call as
`tasks.priority`: *"The batch's window and its stop reason have to survive for
§6's morning queue to render the night."* Neither exists. `ledger.py` declares
`repos`, `runs`, `tasks`, `attempts`, `gate_results`, `failures` and
`findings`, and no `batches`.

Backlog item 16 is the second half, and it is filed separately only because it
was found separately. `repos.policy_sha` is per repo and written once, at cell
start, from the export at `base_sha`. When the default branch has moved,
PACKAGE re-verifies under `fetch_head`'s policy — a *different* declaration,
correctly so — and nothing records that: not the ledger, not the pull request
body, not a watch line. The sha is already in hand at the call site and
discarded as `policy, _`.

§4.1's invalidation rule — *change a repo's gate declarations mid-batch and its
in-flight tasks are invalidated* — is the same question from the other end. It
has no reader today: one cell runs at a time, so a policy cannot move under an
in-flight task because there is no flight. A batch is precisely that window,
which is why this lands before the loop rather than after it.

## Problem

- **A night cannot be rendered.** §6's batch header needs the window and the
  stop reason. No row carries either, so the header would render a confident
  em-dash — the failure §6's own rule names.
- **`runs` cannot be grouped.** Every run is standalone. Nothing can ask which
  runs belonged to one night, which is the question the morning queue is for.
- **A task cannot say what it ran under.** Two different policy declarations
  can govern one task — the export at `base_sha` for its gates, `fetch_head`'s
  for PACKAGE's re-verification — and the ledger records neither against the
  task.

## Acceptance criteria

- [ ] A `batches` table exists carrying `batch_id`, `started_at`, `ended_at`,
      `budget_usd`, `spent_usd_est`, `until_ts` and `status`
- [ ] `status` accepts exactly `DRAINED`, `BUDGET`, `UNTIL` and
      `INFRASTRUCTURE`, and a test asserts a fifth value is rejected
- [ ] `runs` carries a nullable `batch_id`, and a run created outside a batch
      leaves it NULL rather than inventing one
- [ ] `tasks` carries a nullable `policy_sha`
- [ ] The session writes `tasks.policy_sha` at cell start, from the same
      export its gate executables already resolve against — never the working
      copy
- [ ] PACKAGE rewrites `tasks.policy_sha` when re-verification runs under a
      different policy, and leaves it unchanged when it does not; a test drives
      both branches
- [ ] `concurrency` is **not** a column on `batches`, and `tasks.priority` is
      **not** added — both are §4.2.1's explicit cuts
- [ ] A ledger created before this change opens and reads without error, and a
      test asserts it against a database built by the previous schema
- [ ] Existing rows are not backfilled: a `policy_sha` invented for a task
      nobody observed is the "column named for a measurement it cannot make"
      failure §4.1 warns about
- [ ] Every new test runs with no network and no cell

## Out of scope

**Writing a `batches` row from a running batch.** Nothing runs one yet. This
spec lands the schema and the two `policy_sha` writes that have call sites
today; the row is written by the spec that adds the loop.

**Rendering any of it.** `saffron/report/**` is `forbidden`.

**Removing `repos.policy_sha`.** It answers a different question — what the
repo declared when it was last seen — and `upsert_repo`'s callers depend on it.
The new column is per task and additive.

**Deciding what invalidation *does*.** §4.1 says in-flight tasks are
invalidated; acting on that needs a batch to be in flight. This makes the
comparison possible and stops there.

## Notes for the agent

**Read `ledger.py`'s existing migration shapes before inventing a third.**
There are two: `CREATE TABLE IF NOT EXISTS` for new tables, and the
`gate_results_new` rebuild for altering an existing one. Adding a nullable
column to `runs` and `tasks` should need neither a rebuild nor a new style.

**The eighth criterion is the one to write first.** A ledger created by the
previous schema must still open — that is what makes this safe to land on a
database holding every task this repo has run. Build the fixture from the
current schema, then migrate it, then read it.

**`tasks.policy_sha` is written twice by design, and the two writes mean
different things.** At cell start it records what the gates ran under; at
PACKAGE it records what re-verification ran under, and those differ exactly
when the base moved. Overwriting is correct — the last value is what the
packaged commit was verified against — but the sixth criterion asks you to
prove the no-op case too, because a write that always fires is
indistinguishable from one that fires for the right reason.

**Do not add a column you cannot point at a reader for.** §4.2.1 rejects
`tasks.priority` on exactly that ground, and this repo has produced six
instances of the pattern item 18 named. `batch_id`, `policy_sha` and every
`batches` column above have a named reader in §4.2.1 or §6; nothing else does.

`risk: elevated` because `saffron/ledger.py` is in this repo's `elevate_on`.
