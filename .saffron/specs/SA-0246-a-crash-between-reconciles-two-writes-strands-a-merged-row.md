---
id: SA-0246
title: A crash between reconcile's two writes strands a merged row, and the schema guard never saw the column that frees it
type: bug
priority: 2
depends_on: [SA-0227, SA-0226]
estimated_lines: 154
estimate_measured: true
touches:
  - saffron/reconcile.py
  - saffron/ledger.py
  - tests/test_reconcile.py
  - tests/test_ledger.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/projection.py
  - saffron/phases/**
  - tests/test_cli.py
  - tests/test_task.py
  - tests/test_record_migrate.py
  - tests/test_fold.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 24
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      A row in each of the three `PR_PENDING_STATES`, `READY_FOR_REVIEW`,
      `APPROVED` and `CHANGES_REQUESTED`, is driven through a real crash.
      `reconcile` sees its pull request merged, writes the merged head, and
      the state write raises. The next `reconcile` runs against a `gh` that
      exits nonzero for every pull request. It moves all three rows to `MERGED`, lists them in
      `merged`, keeps their merged head, and never asks `gh` about them. A
      `READY_FOR_REVIEW` row in the same scan with no merged head is asked,
      lands in `unasked`, and keeps its state. A third `reconcile` lists
      nothing in `merged`.
    witness: tests/test_reconcile.py::test_a_merge_a_crash_cut_short_completes_on_the_next_reconcile_without_asking
    wrong_versions:
      - The recorded head is checked before the pending-state check, so a `MERGED` row is listed in `merged` on every later scan.
      - "`gh` is asked first and the recorded head is consulted only when the answer is untrusted, so `gh` sees the crashed rows' pull requests."
      - The crashed row is listed in `merged` and its state is never written.
      - The state is written and the row is listed in no bucket.
      - Only a `READY_FOR_REVIEW` row is completed, so the `APPROVED` and `CHANGES_REQUESTED` rows stay pending.
      - Every untrusted answer is read as merged, so the row with no recorded head moves to `MERGED`.
      - "`tasks_by_repo` selects the merged head and `reconcile` never reads it, so every crashed row lands in `unasked`."
  - claim: >-
      A merge `reconcile` observes with no crash still moves the row to
      `MERGED` and records the head GitHub reported, in one scan. That holds
      whether `pushed_sha` differs from that head, equals it, or is absent.
    witness: tests/test_reconcile.py::test_a_merge_records_the_commit_its_pull_request_merged_at
    preserves: true
  - claim: >-
      Every column `PRAGMA table_info(tasks)` reports at head is declared in
      `tests/test_ledger.py`, either with one production function that
      names it in code or as a carve-out with a non-empty reason. The guard
      reports a column declared in neither. It also reports a column whose
      reader is `Ledger.__init__`, `Ledger._apply` or `Ledger._touch_task`,
      sits under `saffron/record/`, or never names the column in code.
      `merged_head_sha`'s reader is `reconcile` in `saffron/reconcile.py`. The
      witness adds an unread column, and the guard names it. It then
      declares as a reader, in turn, each of the three write paths, one
      function under `saffron/record/` and one function that never names
      its column. The guard names that column each time.
    witness: tests/test_ledger.py::test_a_tasks_column_nothing_reads_fails_the_schema_guard
    wrong_versions:
      - The guard checks only that each declared column exists, so a column added with no entry passes.
      - The guard has no list of write paths, so `Ledger._apply` passes as `merged_head_sha`'s reader.
      - The guard accepts a reader under `saffron/record/`, so `_outcome_facts` passes as `merged_head_sha`'s reader.
      - The guard checks that the reader exists and never that it names the column, so `_next_state` passes as `merged_head_sha`'s reader.
      - "`merged_head_sha` stays a carve-out with no reader."
---

## Context

Backlog item **b-3e0dbe**, with **b-1c7019** in the same spec. Both were
found reviewing #381 (`SA-0111`, backlog item 97) on 2026-09-19. Tier 2.
They cite `DESIGN.md` §4.2.1 and §6.1. They share one column. The first
makes `tasks.merged_head_sha` read, and that removes the carve-out the
second's guard would otherwise need for it.

**The two writes.** Read at base `958db033`. `reconcile` walks the rows
`ledger.tasks_by_repo` returns (`saffron/reconcile.py:162`). It skips a row
with no `pr_url` or a state outside `PR_PENDING_STATES`
(`saffron/reconcile.py:168-169`). It asks `gh` through `_pr_status`, and a
`None` answer appends the row to `unasked` and moves on
(`saffron/reconcile.py:170-173`). On a merge with a usable head it calls
`ledger.record_merged_head` and then `ledger.set_task_state`
(`saffron/reconcile.py:186-188`). Each of those commits on its own and
appends its own record fact through `_commit_and_append`
(`saffron/ledger.py:1364-1370` and `:1456-1463`).

**The stranded row.** A crash between the two leaves `merged_head_sha` set
and the state pending. The next scan asks `gh` again. A nonzero exit makes
`_pr_status` return `None` (`saffron/reconcile.py:114-115`), and the row
lands in `unasked`. b-3e0dbe reports that `gh pr view` fails this way once
the merged branch is deleted. No one here measured that. Wherever it holds,
the row lands in `unasked` on every scan and never reaches `MERGED`.

**What the row already says.** The merged head is written only for an
observed merge whose head is a non-empty string
(`saffron/reconcile.py:186`). The ledger's fold sets the column only from a
`task_merged_head` fact (`saffron/ledger.py:795-797`). So a pending row with
a merged head is a row GitHub already answered "merged" for. No reader
looks. `tasks_by_repo` selects `task_id`, `spec_id`, `state`, `pr_url`,
`pushed_sha` and `prompt_sha`, and not the merged head
(`saffron/ledger.py:1001-1002`).

**The guard that missed it.** `test_the_schema_adds_no_column_that_nothing_reads`
(`tests/test_ledger.py:965-991`) asserts the seven `batches` columns, that
`batches` has no `concurrency`, and that `tasks` has no `priority`. It
reaches no other `tasks` column. `DESIGN.md:470` is the rule it is named
for. Outside `saffron/ledger.py`, the one function at base that names
`merged_head_sha` in code is `_outcome_facts`
(`saffron/record/migrate.py:449-450`). It copies the column into the record
and decides nothing.

## Problem

**Finish a merge a crash cut short.** In `reconcile`, take a row that
passes the pending-state check and carries a merged head. It moves to
`MERGED` and is listed in `merged`, without a `gh` call. Every other
row is asked exactly as today. `tasks_by_repo` gains the column so the row carries it. Update
its docstring, which names the columns it returns and why. The settled
call is this read, not one transaction. Each write also appends a record
fact, and SQLite cannot make that append atomic with the row.

**Make the schema guard reach `tasks`.** Keep the test's name and its
`batches` assertions. A rename is barred while a spec is in flight, since
`census` reads a renamed test as a removed one. Add to `tests/test_ledger.py`:

- A mapping from each `tasks` column to one production function that
  reads it, written `path::qualname`. Two examples are
  `saffron/reconcile.py::reconcile` and `saffron/ledger.py::Ledger.queue_lines`.
- A mapping from each column nothing reads to the reason it stays.
- A guard over a ledger's connection. It returns the columns
  `PRAGMA table_info(tasks)` reports in neither mapping. It also returns a
  mapped column whose reader is a refused kind. The kinds are the three
  write paths criterion 3 names, a path under `saffron/record/`, and a
  function that never names the column in code. "Names it in code" means
  a string constant in the function's body matches the column as a whole
  word. The function's own
  docstring does not count, and comments never reach the syntax tree.

The existing test then asserts the guard returns nothing, that no column
is in both mappings, and that every carve-out reason is non-empty.
Criterion 3's witness is a new test beside it.

## Out of scope

- **Any column rename.** b-1c7019 bars it while a spec is in flight.
- **Tables other than `tasks` and `batches`.** The test's name still
  claims the whole schema. `runs`, `attempts` and the rest are left for a
  later item.
- **Whether a reader's result reaches a decision.** The guard checks that
  a named function names the column in code. It does not trace the value
  past that function.
- **Every writer.** The guard refuses three named write paths. Another
  writer, such as `Ledger.create_task`, names columns as payload keys. The
  guard cannot tell it from a reader, so choosing a true reader stays a
  judgement in the test's table.
- **The head move a crashed scan lost.** The scan that crashed printed no
  `head_moved` line. The completion reports none either, since it asks
  nothing.
- **A crash at any other write.** Only the merged-head pair is covered.

## Notes for the agent

**This change is new code.** The completion and the guard are new. So
no criterion declares a mutant, and `witness` reports `skip` for
criteria 1 and 3. Criterion 2 passes at base and must keep passing.
`test_the_merged_head_is_written_before_the_state_moves`
(`tests/test_reconcile.py:470-504`) must also keep passing. The head is
still written first.

**The parents come first.** `SA-0226` and `SA-0227` edit
`saffron/ledger.py`. Their hunks are elsewhere in the file, so the line
numbers above will differ at your base. Find `tasks_by_repo` by name. If a parent adds a `tasks` column, the guard
declares it by the same rule as any other.

**Criterion 1's witness.** Build each crashed row with `_task` and a
merged head, then drive the crash for real. Patch `ledger.set_task_state`
to raise, call `reconcile` with a `_FakeGh` that answers merged, and
expect the raise. Narrow each crash call with `spec_id=`, so one raise
does not stop the other rows. Restore the real method, then assert the
merged head is set and the state is unchanged. For the scan after, a
`_FakeGh({})` exits nonzero for every URL, and its `calls` list is what
"never asks" asserts. Read state and head back through SQL, as `_state`
and `_merged_head` do. Import `PR_PENDING_STATES` and iterate it, so the
witness drives the set the module declares.

**Criterion 3's witness.** Every `tasks` column at head but `prompt_sha`
has a production function naming it in code. Each such function is
outside the three write paths and `saffron/record/`. Measured at base,
`prompt_sha` has two such functions. `Ledger.tasks_by_repo` selects it,
and no caller in `saffron/` subscripts it. `Ledger.create_task` names it
as a fact payload key, which writes it. Declare `prompt_sha` a carve-out
with that reason rather than naming either as its reader. Choose a reader that reads the column, by a
`SELECT` naming it or a row subscript, never one that only writes it. For
the refused kinds, `Ledger.__init__` and `Ledger._apply` both name
`merged_head_sha` in code, and `Ledger._touch_task` names `updated_at`.
`_outcome_facts` names `merged_head_sha`, and `_next_state` does not.
Patch the reader mapping inside a `monkeypatch.context()` per case, so
each case starts from the real mapping.

**Every new witness must fail with the source reverted.** Reverted,
`reconcile` names no `merged_head_sha`. Criterion 3's witness and the
grown schema test both fail on that. Criterion 1's crashed rows land in
`unasked`.

**Measured on a prototype.** On 2026-10-07 a prototype of this change and
both new witnesses ran on a copy of base `958db033`. With the source
reverted, both failed and criterion 2's witness passed. Each wrong version
listed above was applied in turn, and its criterion's witness failed. The
grown schema test failed under "`tasks_by_repo` selects the merged head
and `reconcile` never reads it" as well. The suites in
`tests/test_reconcile.py` and `tests/test_ledger.py` passed whole.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Two of the prototype's docstrings broke the
sentence limit, so read each one back.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`bug` ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). The
prototype counted 615 tokens by `size_gate`, 11 changed lines in the
source and 170 in the tests. At 4 tokens a line that is 154 lines.
