---
id: b-9c7001
title: "`saffron migrate` refuses every ref a live cell started, so 31 merged tasks fold as unmerged"
status: open
tier: 1
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: []
related: [170, b-4eaaa4, b-d4b847]
---

## Problem

Found by running `saffron migrate --from ~/.saffron/ledger.db` on 2026-11-04,
before `SA-0334`'s cutover. Of 371 tasks, 336 migrated and 35 were refused.
Each refusal reads "the record holds N fact(s) that disagree".

The 35 are every task run since #907 (run 44), when cells began writing to
the record. `migrate` appends only when the record's facts equal the first
facts it would write (`saffron/record/migrate.py:104`). A ref a live cell
started never passes. Its first fact, `task_created`, differs from the
ledger's row in four ways:

- `at` keeps microseconds, and the ledger's time is whole seconds.
- `batch_key` is empty on the record and set in the ledger, on 34 tasks.
- `payload.policy_sha` is empty on the record, on 34 tasks.
- `payload.risk` is `standard` on the record and absent in the ledger, on 20.

The record also holds kinds the ledger never writes: `task_engine`,
`task_policy`, `spec_finding`, and a `task_push` and `task_state` per state.

The ledger holds facts written after the task's one push (b-4eaaa4). On the
mirror a later fetch with `+refs/*:refs/*` replaced them with origin's ref,
so the ledger is now their only copy:

| Kind | Tasks the record lacks it on |
|---|---|
| `task_merged_head`, and the `MERGED` state | 31 |
| `stack_layer` | 27 |
| `end_review` | 26 |
| `qualification` | 18 |
| a later `attempt_opened` and `attempt_closed` | 11 |
| a later `finding` | 13 |
| `task_package` | 5 |

A fold of the mirror gives back 371 tasks, but no `MERGED` row. The ledger
holds 31. The fold has 28 at `READY_FOR_REVIEW` and four at `EXHAUSTED`,
`SA-0330` among them. `reconcile` will not stamp them again, since the ledger
already reads `MERGED`. `SA-0335` pushes later facts from now on but repairs
none of these.

Per kind, ignoring `at` and the gate result's `schema_version`, `collected`
and `uncollected`, each of the 35 refs holds the first N of the ledger's
facts. What is missing is a clean tail per kind.

## Done looks like

`saffron migrate` tops up a ref a live cell started. Each kind's facts on the
record must match the ledger's first ones. Then it appends the rest of each
kind and the ledger's final state, and pushes. Any other mismatch is still
refused. Run on the live ledger, it refuses none of the 35, and a fold gives
back the ledger's 31 `MERGED` rows.

## Record

- 2026-11-04: filed from `saffron migrate`'s live run before `SA-0334`'s
  cutover. The operator chose the arm: migrate tops up by kind.
