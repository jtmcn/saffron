---
id: SA-0179
title: A qualification fact has no table and no write, so nothing records what the host decided of a finding
type: feature
priority: 1
depends_on: [SA-0178]
touches:
  - saffron/ledger.py
  - tests/test_ledger_qualifications.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/probe.py
  - saffron/end_review.py
  - saffron/qualify.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/**
  - tests/test_session.py
  - tests/test_probe_cell.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_findings.py
  - tests/test_end_review.py
  - tests/test_batch.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
budget_usd: 18
max_attempts: 3
max_turns: 100
estimated_lines: 260
pending_symbols:
  - saffron/ledger.py::record_qualification
acceptance:
  - claim: >-
      `Ledger.record_qualification(task_id, *, finding, filed, outcome,
      reason)` writes one `qualification` fact under the task's key, and
      places it as one `qualifications` row. The row's `position` is one
      more than that task's rows so far. Its `lens`, `file`, `line`,
      `claim` and `probe_verdict` are the finding's, its `severity` is
      `filed`, and its `outcome` and `reason` are as given. The witness
      interleaves two tasks' writes. It drives the outcomes `qualified`,
      `killed`, `unverified`, `unanchored` and `note`, the verdicts
      `survived`, `killed`, `unproven` and none, a reason that is not
      empty, and a `filed` that differs from the finding's severity.
    witness: tests/test_ledger_qualifications.py::test_a_qualification_is_one_fact_and_one_row_numbered_within_its_task
  - claim: >-
      Folding the record into a fresh ledger, whose task ids differ,
      rebuilds the same `qualifications` rows. Folding it into the ledger
      that wrote them leaves them as they were. `fold_task` with one task's
      key and no facts removes that task's rows and no other. The witness
      drives two tasks, and a fresh ledger that holds an unrelated task
      before the fold.
    witness: tests/test_ledger_qualifications.py::test_the_fold_rebuilds_each_tasks_qualifications_and_drops_one_task_alone
  - claim: >-
      A fact kind the ledger does not place still aborts the fold.
    witness: tests/test_ledger_fold_task.py::test_a_kind_the_ledger_cannot_place_aborts_the_fold_in_either_mode
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 4 of its Done. It cites `DESIGN.md` §4.1
and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "Qualification is
host code", is the design.

**Step 4 is three specs.** `SA-0178` lets the host probe any findings.
This spec adds the table that records what the host decided of each
finding, and the method that writes it. `SA-0147` qualifies an end
review's findings and calls this spec's method once per finding. The
three were one spec, `SA-0147`, until its cell ended `PLAN_REJECTED` on
2026-09-26 over the `size` ceiling.

**What the tree base holds.** This spec's tree base is `SA-0178`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:165-166`, `:213`). `SA-0178` edits
`saffron/cell/session.py` alone, so every line below stands as read at
`eb7b7d37`.

**The fact kind exists.** `qualification` is in `KINDS`
(`saffron/record/contract.py:40`) and in `ontology/factory.ttl` (`:193`).
No branch of `_apply` places it. `_apply` raises on a kind it has no
branch for (`saffron/ledger.py:718`).

**Recording today.** Each write method builds one fact with `_build_fact`
(`saffron/ledger.py:406-425`) and hands it to `_commit_and_append`
(`:433-438`). That applies the fact, commits, then appends it to the
record. `record_end_review` is the nearest shape
(`:1273-1291`). Its table, `end_reviews`, is keyed on the record key and
references no other table (`:189-199`). So a fold into a fresh ledger
places it. `_apply` inserts its row with `fact.task_key` (`:674-686`).
`fold_task` drops a task's rows through `_drop_task_rows`, then applies
its facts again (`:442-446`). `_drop_task_rows` deletes `stack_layers` and
`end_reviews` rows by the key first (`:448-454`). `fold` folds every task
in the record through `fold_task` (`saffron/record/fold.py:42-65`).

**The module docstring** counts the thirteen kinds that fold back
(`saffron/ledger.py:6-7`). It names `stack_layers`, `end_reviews` and
`baseline_names` as a tenth, eleventh and twelfth table (`:12-14`).

## Problem

Build two things in `saffron/ledger.py`.

1. **The table.** Add `qualifications` to `SCHEMA`, with no reference to
   another table:

   | column | type |
   |---|---|
   | `task_key` | `TEXT NOT NULL` |
   | `position` | `INTEGER NOT NULL` |
   | `lens` | `TEXT NOT NULL` |
   | `severity` | `TEXT NOT NULL` |
   | `file` | `TEXT NOT NULL` |
   | `line` | `INTEGER` |
   | `claim` | `TEXT NOT NULL` |
   | `probe_verdict` | `TEXT` |
   | `outcome` | `TEXT NOT NULL` |
   | `reason` | `TEXT NOT NULL` |

   Its primary key is `(task_key, position)`. The row carries the finding
   itself, so it reads alone.
2. **The write and its fold.** Add `record_qualification`, as criterion 1
   states. It builds one `qualification` fact with `_build_fact` and
   writes it through `_commit_and_append`. The payload carries `position`
   and every column but `task_key`. `_apply` places the fact as one row,
   `task_key` from the fact and the rest from the payload.
   `_drop_task_rows` deletes the key's rows beside the other two tables
   keyed on it.

`outcome` is one of `qualified`, `killed`, `unverified`, `unanchored` and
`note`, and `reason` is empty except for `unverified`. `SA-0147` holds
both rules. This method records what it is given.

The module docstring's count of kinds that fold back becomes fourteen, and
`qualifications` joins its list of tables `DESIGN.md` §4.1 does not
name. The `_drop_task_rows` docstring names it with the other two.

No production code calls `record_qualification` until `SA-0147` does. So
it is a `pending_symbols` entry, and the `dead` gate defers it while this
spec is open (`.saffron/gates/dead.py:4-6`, `:113-127`).

## Out of scope

- **Deciding a finding's outcome.** `SA-0147` builds `saffron/qualify.py`.
- **A read method.** `SA-0174` adds one, for the delegate's findings file.
- **A `CHECK` on `outcome`.** The table records what `SA-0147` decides,
  and `SA-0147`'s witness pins the five values.
- **`DESIGN.md` §4.1's schema sketch.** It gains no `qualifications` here.
  `DESIGN.md` is protected.
- **The vocabulary.** `CONTEXT.md` has no entry for qualification.
  Backlog item b-466005 files it by hand.

## Notes for the agent

**Criteria 1 and 2 are new code.** No text at the tree base names the
table or the method. So they declare a witness and no mutant, and
`witness` reports `skip` for them. Criterion 3 is `preserves` and names a
test that passes at the tree base.

**Both witnesses call the new method on a `Ledger`**, so the reverted run
fails with `AttributeError` rather than failing to collect. Read the rows
with `sqlite3` on the ledger's file, ordered by `task_key` and `position`.

**The arrangement.** A `Ledger` on a `tmp_path` file with a
`MemoryRecord`. One repo, and two runs with a task each, `TE-1` and
`TE-2`.

**Criterion 1's witness** makes five writes, in this order:

| task | claim | lens | at | finding's severity | its verdict | `filed` | outcome | reason |
|---|---|---|---|---|---|---|---|---|
| `TE-1` | q1 | `spec` | `src/a.py:3` | blocker | `survived` | concern | `qualified` | empty |
| `TE-2` | q2 | `standards` | `src/b.py:7` | note | `killed` | blocker | `killed` | empty |
| `TE-1` | q3 | `correctness` | `src/a.py:4` | concern | `unproven` | concern | `unverified` | "why" |
| `TE-2` | q4 | `join` | `src/c.py:9` | concern | none | concern | `unanchored` | empty |
| `TE-1` | q5 | `adequacy` | `src/b.py:5` | note | none | note | `note` | empty |

It asserts the five rows whole. `TE-1` holds q1, q3 and q5 at positions
1 to 3, and `TE-2` holds q2 and q4 at 1 and 2. Each row's lens, file and
line are its finding's, and its severity is its `filed`. It asserts that `TE-1`'s facts in the record are its
`task_created` fact and three `qualification` facts.

**Criterion 2's witness** writes q1, q2 and q3 as above. It opens a fresh
`Ledger` with no record and creates an unrelated repo, run and task there.
It folds the record into the fresh ledger, and asserts its rows equal the
source's. It folds the record into the source ledger, and asserts the
rows unchanged. Last, `fold_task` on the fresh ledger with `TE-2`'s key and
no facts leaves `TE-1`'s two rows alone.

These fail them, each measured:

- `_apply` with no branch for `qualification`, which raises in the fold
- `_drop_task_rows` that leaves the rows, which raises on the primary key
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `TE-2`'s rows after `fold_task(key, [])`
- the severity read from the finding rather than `filed`
- `position` counted over the whole table, not per task

**How the list was measured.** A throwaway test ran on 2026-09-26 at
`eb7b7d37`. It subclassed `Ledger` with this table and method, and a wrong
version of each. The right build passed both witnesses, and each wrong
version failed at least one.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, a hedge or
a sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`).
`SA-0145` and `SA-0153` each added a table and its write, and measured 312
and 319 tokens in `ledger.py` with `size_gate`. This one is about 70
changed lines at 4.8 tokens a line, about 340 tokens. The two witnesses
come to about 120 formatted lines at 3.4, about 410. That is about 750
tokens. Sibling cells landed at 1.4 to 1.6 times their authors'
estimates, so about 1050, 35% of the ceiling.
