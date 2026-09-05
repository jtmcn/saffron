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
      differ between `base_sha` and `fetch_head`. A recorded sha of NULL counts
      as different and is written: it means nothing recorded what this task ran
      under, which is the gap the spec exists to close.
    witness: tests/test_package.py::test_reverifying_under_a_changed_policy_records_the_policy_it_used
  - claim: >-
      When the two declarations are identical, PACKAGE issues no policy write
      at all — the recording method is not called. An unconditional write
      satisfies the previous claim while being wrong, and only this one can
      tell them apart. Asserted on the call, never on `updated_at`: PACKAGE
      moves that column on every non-raising return anyway, through
      `record_push` and `set_task_package`.
    witness: tests/test_package.py::test_reverifying_under_an_unchanged_policy_issues_no_policy_write
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
write, which is also wrong, and only the no-op case can tell them apart.

**Assert it on the call, not on the row.** `updated_at` is the obvious
observable and it does not work here: `package()` moves that column on every
non-raising return, through `record_push` and `set_task_package`, so a correct
implementation fails a test written that way. It is also `datetime('now')` at
second resolution, so two writes inside one second are indistinguishable
anyway. Wrap or monkeypatch the recording method and assert it was not called.

**The no-op branch has to be built, not inherited.** `packageable`'s task row
is created with no `policy_sha`, so it is NULL — which is the *differs* branch
by the rule above, not the unchanged one. The no-op test must first seed the
row with the sha256 of the fixture's committed `policy.yaml` bytes.

**`policy_sha` is a hash of `policy.yaml`'s bytes, not of the tree.** The two
declarations differ exactly when that file's contents changed between
`base_sha` and `fetch_head` — **not** whenever the base moved. A base can move
a hundred commits without `policy.yaml` changing a byte, and a test that moves
the base and expects a rewrite is testing the wrong thing.

**Writing `policy.yaml` in the fixture's working copy does not reach
`fetch_head`.** Two of the three existing tests that touch it write the working
copy only and never commit — that is their whole point, that the checkout's
policy does not govern. The differs branch needs a `git commit` *and* a push to
the default branch inside the fixture's repo, the way the test that names a
policy fault at the default-branch head does. Copy that one, not the nearer-
looking ones.

**Both writes are additive, and any new parameter must default.**
`saffron/replay.py` calls `create_task` and is `forbidden` here, as are three
test modules outside `touches`. A required parameter breaks callers this spec
cannot legally repair.

**Read `ledger.py`'s migration shapes before inventing a new one**, and use the
guarded `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` one — `CREATE TABLE IF
NOT EXISTS` is a no-op on a `tasks` table that already exists, which is every
ledger there is. `SA-0045` added a second block of exactly this shape for
`runs.batch_id`, and this spec is cut from that branch, so there is a worked
example one commit back.

**Two size economies, because this spec is the wider of the pair.** The first
witness is a near-copy of `SA-0045`'s `batch_id` migration test — share one
old-schema helper between it and the fifth rather than building the fixture
twice. And the `tests/test_package.py` tests run 25–40 lines each, which is
where the ceiling pressure is.

**The sixth witness is a new test and `preserves` is correctly `false`.** Its
claim reads like a preservation — the repo-level column keeps working — but a
new test cannot preserve, because it did not pass at base. Flipping it to
`true` fails with `witness-not-preserved`.

**Do not add `policy_sha` to `queue_lines`.** It selects explicit columns and
feeds the morning queue, and `saffron/report/**` is `forbidden` here — a column
added there would render nowhere and read as a reader that does not exist.

**No new test may carry the `cell` marker, and this is the one that would burn
the budget silently.** `pyproject.toml` sets `addopts = "-m 'not cell'"`, and
the `tests` gate passes the same argv to `--collect-only` deliberately. A
cell-marked witness is therefore never collected at head, `criteria` reports
`witness-not-collected`, the gate fails, and the attempt is spent — three
times, on a test that was correct. Every witness here is reachable without a
container: the session tests already drive `run_one_cell` end to end against a
stubbed runtime, and that helper already takes a base-policy argument, which is
the knob witnesses 2 and 6 need.

`risk: elevated` because `saffron/ledger.py` and `saffron/cell/**` are both in
this repo's `elevate_on`.
