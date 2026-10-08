---
id: SA-0251
title: A merged draft leaves its `EXHAUSTED` task `EXHAUSTED`, so `reconcile` never admits its child
type: bug
priority: 2
depends_on: [SA-0246]
estimated_lines: 130
estimate_measured: true
touches:
  - saffron/reconcile.py
  - tests/test_reconcile.py
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
  - hooks/**
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/intake.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/view/**
  - tests/test_scheduler.py
  - tests/test_cli.py
  - tests/test_task.py
  - tests/test_package.py
  - tests/test_ledger.py
  - tests/test_queued_specs.py
budget_usd: 16
max_attempts: 3
max_turns: 90
acceptance:
  - claim: >-
      `reconcile` asks GitHub about a task row that is `EXHAUSTED` and
      carries a `pr_url`. When the answer is a merged pull request, the row
      becomes `MERGED` and its id lands in the result's `merged` list. The
      head GitHub reported is written to `merged_head_sha`. A reported head
      that differs from the row's `pushed_sha` lands in `head_moved`. The
      witness drives one such row, whose reported head is a sha other than
      the one PACKAGE pushed.
    witness: tests/test_reconcile.py::test_a_merged_draft_moves_its_exhausted_task_to_merged
    mutant:
      file: saffron/reconcile.py
      find: 'if state == "MERGED":'
      replace: 'if state == "MERGED!":'
    wrong_versions:
      - A version that writes `MERGED` through `set_task_state` alone and never records the merged head.
      - A version that skips an `EXHAUSTED` row before the head comparison, so a moved head is never reported for it.
  - claim: >-
      Every other answer about an `EXHAUSTED` row's pull request leaves the
      row `EXHAUSTED`, and its id reaches none of the `merged`, `rejected`,
      `changes_requested` or `approved` lists. The witness asks once per row
      and drives every answer `_pr_status` can return. Those are closed,
      open with changes requested, open and marked ready, open as a draft,
      open with no `isDraft` field, and an unrecognised `state`. They also
      include the three answers `_pr_status` turns into `None`, which are a
      non-zero exit, unparseable output and a JSON value that is not an
      object. Each of those three rows lands in `unasked`. Two `EXHAUSTED`
      rows with no pull request, one with a NULL `pr_url` and one with an
      empty one, are never asked and stay `EXHAUSTED`.
    witness: tests/test_reconcile.py::test_an_exhausted_task_moves_on_no_answer_but_a_merge
    mutant:
      file: saffron/reconcile.py
      find: 'result.unasked.append(row["task_id"])'
      replace: 'result.unasked.clear()'
    wrong_versions:
      - A version that adds `EXHAUSTED` to the pending set with no other change, so a closed draft writes `REJECTED` and a ready one writes `APPROVED`.
      - A version that drops an `EXHAUSTED` row silently when `gh` gives no answer, so it never reaches `unasked`.
      - A version that appends a non-merged `EXHAUSTED` row to its bucket while leaving the state unwritten.
      - A version that asks about an `EXHAUSTED` row whose `pr_url` is empty.
  - claim: >-
      A child spec whose `depends_on` parent has one task, `EXHAUSTED` with
      a draft pull request, is refused by `build_queue` on that dead state.
      After `reconcile` reads a merged answer for the draft, the parent's
      task reads `MERGED`. The same `build_queue` call then admits the
      child as a candidate and refuses nothing. The witness drives the scan
      before and after over one spec directory and one ledger.
    witness: tests/test_reconcile.py::test_a_merged_exhausted_parent_admits_its_child_to_the_queue
    mutant:
      file: saffron/scheduler.py
      find: 'DEPENDENCY_MERGED = "MERGED"'
      replace: 'DEPENDENCY_MERGED = "MERGED_ANYWHERE"'
    wrong_versions:
      - A version that moves the parent to `APPROVED` rather than `MERGED`, which admits the child for stacking but never as merged.
  - claim: >-
      A `READY_FOR_REVIEW` row still moves on more than a merge. A closed
      pull request writes `REJECTED`, changes requested write
      `CHANGES_REQUESTED`, and a merge writes `MERGED`.
    witness: tests/test_reconcile.py::test_a_head_is_recorded_only_for_an_observed_merge
    preserves: true
---

## Context

Backlog item **b-8e30bd**, raised by `SA-0204`'s writer and reviewers in
the spec loop's run 28. It cites `DESIGN.md` §4.2.1 and §6.1. Every line
number below was read at `958db033`.

**`SA-0204` leaves an open draft under `EXHAUSTED`.** PACKAGE in its
`exhausted` mode records every state as `EXHAUSTED`
(`saffron/phases/package.py:636-640`). `_finish` writes that state with
the draft's `pr_url` through `set_task_package`
(`saffron/phases/package.py:1001-1009`). A PACKAGE refusal writes the
default empty `pr_url` instead (`saffron/phases/package.py:595-597`).

**`reconcile` skips every `EXHAUSTED` row.** `PR_PENDING_STATES` holds
`READY_FOR_REVIEW`, `APPROVED` and `CHANGES_REQUESTED`
(`saffron/reconcile.py:49`). The loop skips a row with no `pr_url` or a
state outside that set (`saffron/reconcile.py:168-169`). So nothing ever
asks GitHub about the draft, and nothing writes `MERGED` for it.

**The scheduler then refuses the child.** `DEPENDENCY_DEAD_STATES` holds
`REJECTED` and `EXHAUSTED` (`saffron/scheduler.py:105`). A parent whose
only rows are dead refuses its child with "will not merge as it stands"
(`saffron/scheduler.py:634-638`). A parent with a merged row under any
spec sha joins `merged_anywhere` (`saffron/scheduler.py:920-927`). That
set admits the child first (`saffron/scheduler.py:589-590`). The
`pushed_landed` admission reads the recorded `pushed_sha`
(`saffron/scheduler.py:931-947`). A squash merge does not land that
commit, so it misses this case.

**What the loop does with an answer today.** `_pr_status` returns `None`
on three answers (`saffron/reconcile.py:108-120`). They are a non-zero
exit, unparseable output and a JSON value that is not an object. The
loop counts that row in `unasked` (`:171-173`). It compares the reported head with `pushed_sha`
before it maps the state (`:174-177`). `_next_state` maps the answer to
`MERGED`, `REJECTED`, `CHANGES_REQUESTED`, `APPROVED` or `None`
(`:123-141`). A merge records the head before the state moves
(`:186-188`).

**Who reconciles before a scan.** `_resolve_queue` calls `reconcile`
before `build_queue` (`saffron/cli.py:1327-1331`). `saffron queue` and
every batch scan reach it. The stacking resolver calls `reconcile`
narrowed to one parent's `spec_id` (`saffron/task.py:255`).

The fixture in criterion 3, run at `958db033` with a prototype of this
change, printed this before and after the reconcile. Each line is the
candidates' ids, then each refusal's file and reason.

```
before [] [('a.md', 'depends_on TE-0 is EXHAUSTED, which will not merge as it stands — a different fact about the night from a parent not yet run')]
after ['TE-1'] []
```

## Problem

A draft PACKAGE opened for an `EXHAUSTED` task can merge, and the ledger
never learns it. The task stays `EXHAUSTED`, so every spec that depends
on it stays refused, and the next night skips them.

Have `reconcile` also ask about an `EXHAUSTED` row that carries a
`pr_url`. Apply only a merged answer, through the same writes a merge
makes for a `READY_FOR_REVIEW` row. Every other answer leaves the row
exactly as it was. An answer `gh` could not give is still counted in
`unasked`.

A closed draft leaves the row `EXHAUSTED`, the outcome PACKAGE recorded
(§5.7). A ready answer is not `APPROVED` either. The task never passed
REVIEW, so the merge train has nothing to admit.

The comment above `PR_PENDING_STATES` says which rows are worth asking
about (`saffron/reconcile.py:46-49`). Keep it true for the rows the loop
now asks.

## Out of scope

- **The module docstring** (`saffron/reconcile.py:1-27`). `SA-0243`
  rewrites its account of PACKAGE's last word. Leave those lines as they
  are, so the two pull requests touch separate hunks.
- **The crash between the two merge writes.** `SA-0246` is drafted to
  complete a row whose `merged_head_sha` is set, without asking GitHub.
  This spec depends on it. Do not move or re-guard that path.
- **The ledger's account of PACKAGE's states.** The `set_task_package`
  docstring names `READY_FOR_REVIEW` and `MERGE_FAILED` only
  (`saffron/ledger.py:1494-1500`). `SA-0204` left it stale, and
  `saffron/ledger.py` is `forbidden` here.
- **A closed draft is asked again on every scan.** Its row stays
  `EXHAUSTED` with its `pr_url`, so each later reconcile asks once more.
  The count is one `gh pr view` per such row per scan.
- **A resumed task's earlier pull request.** The unpackaged push writes
  only `record_push` (`saffron/phases/package.py:1239`), never `pr_url`.
  So a resumed task that ends `EXHAUSTED` unpackaged keeps its earlier
  attempt's `pr_url`. A merge of that pull request also becomes `MERGED`,
  which is still true of the spec's branch.
- **The window while PACKAGE runs.** `_drive_cell` writes the state
  before PACKAGE starts (`saffron/reconcile.py:15-26`, backlog item
  b-dce9a4). A merged answer read in that window is overwritten by
  PACKAGE's own write, as for any row.
- **Protected text.** `DESIGN.md` §3.3 and §5.7 describe `EXHAUSTED` with
  no way out. The operator edits them in this spec's own pull request.

## Notes for the agent

**The change edits existing code**, so each non-`preserves` criterion
declares a mutant on text the base already holds. Criteria 1 and 2 pin
lines of `saffron/reconcile.py` the change leaves in place. Criterion 3
pins the scheduler's merged state, which the child's admission reads.
`saffron/scheduler.py` is `forbidden` because the change never edits it.
Criterion 4 names a test that passes now. It keeps a `READY_FOR_REVIEW`
row moving on a closed and a changes-requested answer.

**At base every new witness fails.** No `EXHAUSTED` row is asked, so
criterion 1's row stays `EXHAUSTED` and criterion 2's asks list is empty.
Criterion 3's child stays refused after the reconcile.

**Building the rows.** Write each `EXHAUSTED` row the way PACKAGE does,
through `ledger.set_task_package` with the state, a branch, a pushed sha
and the `pr_url` (`saffron/ledger.py:1483-1515`). The NULL row in
criterion 2 is a task created and set `EXHAUSTED` with no package write.
Reuse `_task`, `_FakeGh`, `_state`, `_merged_head`, `_PUSHED` and `_FIXED`
from `tests/test_reconcile.py`.

**Criterion 2's `gh`** answers per URL and records each URL it was asked.
It returns a non-zero exit for one row, `not json` for another, and `[]`
for a third. The other six rows each get one answer from the claim. The
witness asserts the recorded URLs equal the nine rows' URLs, each once.

**Criterion 3's fixture** writes two spec files into a temporary
directory. The parent declares nothing else, and the child names it in
`depends_on`. The parent's task sits at the parent's own `spec_sha`, read
with `intake.load_spec`. Import `build_queue` inside the test or at the
top of the module, since it exists at base. Before the reconcile, assert
the refusal list holds the child alone and its reason names `EXHAUSTED`.
A child refused for another reason then fails the witness.

**What criterion 1 leaves undriven.** Three merged answers carry no
usable head. It is absent, empty or not a string. The witness drives
none of the three for an `EXHAUSTED` row.

**Wrong versions.** Each criterion lists the ones its witness must kill.
A prototype's witnesses killed each of them on 2026-10-07, and passed
with the fix.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** No touched path is in `elevate_on`, so `size` is advisory. A
prototype with all three new witnesses measured 475 tokens with
`size_gate`'s counter, against the `bug` ceiling of 1300.
`estimated_lines` is that count over four, plus a margin for the comment
above the pending set.
