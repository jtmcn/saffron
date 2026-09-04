---
id: SA-0046
title: a task cannot say which policy it ran under, and two of them can govern one task
type: feature
priority: 1
depends_on:
  - SA-0045
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - tests/test_ledger.py
  - tests/test_session.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - saffron/replay.py
budget_usd: 10
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      `tasks` carries a nullable `policy_sha`, added the way a column on an
      existing table has to be — the guarded `ALTER TABLE` this module already
      uses, never `CREATE TABLE IF NOT EXISTS`, which does not alter.
    witness: tests/test_ledger.py::test_a_ledger_built_by_the_previous_schema_gains_policy_sha
  - claim: >-
      The session records, at cell start, the policy its gates will run under —
      read from the export at `base_sha` that the gate executables already
      resolve against, never from the working copy.
    witness: tests/test_session.py::test_a_task_records_the_policy_its_gates_ran_under
  - claim: >-
      PACKAGE rewrites the task's `policy_sha` when re-verification runs under
      a different declaration, which is what happens when `policy.yaml`'s bytes
      differ between `base_sha` and `fetch_head`.
    witness: tests/test_package.py::test_reverifying_under_a_changed_policy_records_the_policy_it_used
  - claim: >-
      When the two declarations are identical, PACKAGE leaves the row alone —
      `updated_at` does not move. An unconditional write satisfies the previous
      claim while being wrong, and only this one can tell them apart.
    witness: tests/test_package.py::test_reverifying_under_an_unchanged_policy_does_not_touch_the_row
  - claim: >-
      A task row created before this change reads back with a NULL
      `policy_sha`, never a value invented for a task nobody observed.
    witness: tests/test_ledger.py::test_an_existing_task_is_not_backfilled_with_a_policy_sha
  - claim: >-
      `repos.policy_sha` is unchanged and still written. It answers a different
      question — what the repo declared when it was last seen — and
      `upsert_repo`'s callers depend on it.
    witness: tests/test_session.py::test_the_repo_level_policy_sha_is_still_written
---

## Context

Backlog item 16. `repos.policy_sha` is per repo, rewritten on every cell start
from the export at `base_sha`. When the default branch has moved, PACKAGE
re-verifies under `fetch_head`'s policy — a *different* declaration, correctly
so — and nothing records that: not the ledger, not the pull request body, not a
watch line. The sha is already in hand at the call site and discarded as
`policy, _`.

**Two declarations can govern one task**, and the ledger records neither
against it. The repo-level column answers a different question — what the repo
declared when it was last seen — and cannot answer this one.

§4.1's invalidation rule — *change a repo's gate declarations mid-batch and its
in-flight tasks are invalidated* — is the same question from the other end. It
has no reader today: one cell runs at a time, so a policy cannot move under an
in-flight task because there is no flight. A batch is that window, which is why
this lands before the loop rather than after it. This spec makes the comparison
*possible*; acting on it needs a batch to be in flight and is not here.

## Problem

- **A task cannot say what it ran under.** Its gates ran under one declaration
  and its re-verification may have run under another, and the row records
  neither.
- **The sha is in hand and thrown away.** `load_policy` returns it at PACKAGE's
  call site and it is bound to `_`.
- **§4.1's invalidation rule is a claim with no reader.** Nothing can compute
  it, so nothing can be wrong about it, so it has never been tested.

## Out of scope

**Acting on invalidation.** §4.1 says in-flight tasks are invalidated. Doing
something about it needs a batch; this makes the comparison possible and stops.

**The `batches` table and `runs.batch_id`.** `SA-0045`, merged before this.

**Removing or changing `repos.policy_sha`.**

**Rendering it.** `saffron/report/**` is `forbidden`.

## Notes for the agent

**The fourth witness is the one to write first, and it is why this spec is not
one criterion.** "Rewrites when it differs" is satisfied by an unconditional
write, which is also wrong. Only "does not touch the row when it does not
differ" can tell a correct implementation from a lazy one, and `updated_at` is
the observable that distinguishes them. `SA-0047` uses the same device for the
same reason, on a task that must not be re-stamped.

**`policy_sha` is a hash of `policy.yaml`'s bytes, not of the tree.** The two
declarations differ exactly when that file's contents changed between
`base_sha` and `fetch_head` — **not** whenever the base moved. A base can move
a hundred commits without `policy.yaml` changing a byte, and a test that moves
the base and expects a rewrite is testing the wrong thing. `tests/test_package.py`
already has tests that mutate `policy.yaml` at `fetch_head` through the
`packageable` fixture; that is the "differs" branch, and the unmutated fixture
is the no-op branch.

**Both writes are additive, and any new parameter must default.**
`saffron/replay.py` calls `create_task` and is `forbidden` here, as are three
test modules outside `touches`. A required parameter breaks callers this spec
cannot legally repair.

**Read `ledger.py`'s three migration shapes before writing a fourth**, and use
the guarded `ALTER TABLE ADD COLUMN` one — `CREATE TABLE IF NOT EXISTS` is a
no-op on a `tasks` table that already exists, which is every ledger there is.

**Every new test runs with no network and no cell**, except any that must
drive a real session, which carries the `cell` marker.

`risk: elevated` because `saffron/ledger.py` and `saffron/cell/**` are both in
this repo's `elevate_on`.
