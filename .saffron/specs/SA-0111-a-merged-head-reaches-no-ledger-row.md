---
id: SA-0111
title: the head a pull request merged at is printed once and stored nowhere, so a task recorded MERGED keeps no trace of the tree that went in
type: bug
priority: 2
depends_on: []
touches:
  - saffron/ledger.py
  - saffron/reconcile.py
  - tests/test_ledger.py
  - tests/test_reconcile.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - pyproject.toml
  - uv.lock
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/chain_walk.py
  - saffron/projection.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/events.py
  - saffron/intake.py
  - saffron/preflight.py
  - saffron/probe.py
  - saffron/replay.py
  - saffron/watch.py
  - saffron/repos/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/agents/**
budget_usd: 20
max_turns: 120
acceptance:
  - claim: >-
      When `reconcile` moves a task to `MERGED`, the task's ledger row keeps the
      head commit GitHub reported for that pull request, whatever the row's
      `pushed_sha`: a head that differs from the commit PACKAGE pushed, a head
      that is that same commit, and a row that carries no packaged commit at
      all. Today nothing on that path writes a sha, and the head is gone by the
      next scan.
    witness: tests/test_reconcile.py::test_a_merge_records_the_commit_its_pull_request_merged_at
  - claim: >-
      A merge GitHub answered with no usable head — the field absent from the
      answer, present and empty, or present and not a string — still moves the
      task to `MERGED` and records no head at all. The commit PACKAGE pushed is
      never written in its place, so a row that carries a head is a head that
      was observed. A pull request that is not merged records no head either,
      whatever its state moves to: an answer that moves a row to
      `CHANGES_REQUESTED`, and one that moves a row to `REJECTED`, each over a
      head other than the packaged commit, leave the column exactly as it was.
    witness: tests/test_reconcile.py::test_a_head_is_recorded_only_for_an_observed_merge
  - claim: >-
      A ledger built by the previous schema opens, keeps the task rows it
      already had, and accepts the new write, so the ledger this defect was
      measured against records the next merge it reconciles instead of raising
      on a column it does not have.
    witness: tests/test_ledger.py::test_a_ledger_built_before_the_merged_head_column_gains_it_and_records_one
---

## Context

Backlog item 97 is
`docs/backlog/097-a-delegate-s-review-fixes-reach-a-task-s-pull-request-and-no-gate.md`,
tier 1. Its minimum shipped on 2026-09-10. `reconcile` now asks GitHub for a
pull request's head beside its state, and names every pending pull request
whose head is not what PACKAGE pushed. The item's Record names two things
still owed. One is the task's gates re-run over the new head. The other is a
record. This spec is the record half. The re-gate stays open on the item.

Every sentence below about current code was read at `origin/main` (`0e84d4c3`)
on 2026-09-19.

**The head is asked for, compared, printed, and dropped.** `_pr_status` at
`saffron/reconcile.py:105-115` asks `gh pr view` for
`state,reviewDecision,headRefOid`. `reconcile` unpacks that head beside the
row's `pushed_sha` at `saffron/reconcile.py:158-160`. It records a `HeadMoved`
where both values are real shas and the two differ. `saffron/cli.py:1014-1019`
prints one line per moved head. The comment on the `head_moved` field at
`saffron/reconcile.py:100-101` says what happens next: "Reported, never
written".

**The merge path writes one column.** The single ledger call on that path is
`ledger.set_task_state(row["task_id"], new_state)` at
`saffron/reconcile.py:169`. `set_task_state` at `saffron/ledger.py:610-622`
updates `state`, `updated_at`, and the spend rolled up from the task's
attempts. No sha reaches it. The `tasks` table at `saffron/ledger.py:64-79`
carries `pushed_sha` at `:73` and `pr_url` at `:74`. It holds no column for the
commit a pull request merged at.

**Only the scan that sees a merge can ask about it.**
`saffron/reconcile.py:151` skips every row whose state is outside
`PR_PENDING_STATES`. `MERGED` is outside that set, at
`saffron/reconcile.py:48`. The comment at `saffron/reconcile.py:45-47` gives
the reason. `MERGED` and `REJECTED` are excluded so that "never moves
backwards" holds once a merged branch is deleted and `gh pr view` starts
erroring on it. The module already knows this. Its head comparison sits before
the state check at `saffron/reconcile.py:157`, under a comment calling a merge
the last time this row is asked. `tests/test_reconcile.py:223-243` pins that
ordering. The one chance is spent on a line of terminal output.

**`reconcile` is the only writer of `MERGED`.** `_next_state` at
`saffron/reconcile.py:118-131` returns it for a pull request GitHub reports as
merged. A `git grep` for that state under `saffron/` at this base returns
eleven lines outside `saffron/reconcile.py`. Every one reads the state or
labels it: `saffron/chain_walk.py:95`, `:104` and `:115`,
`saffron/cli.py:999`, `saffron/projection.py:373`, and
`saffron/scheduler.py:10`, `:68`, `:84`, `:506`, `:615` and `:796`. There is
one place to write the head, and this change stays inside it.

**How often it matters was measured.**
`docs/evidence/2026-09-10-review-fixes-past-package.md` holds the count. 34 of
this repo's 38 packaged pull requests merged at a head other than the one
PACKAGE pushed. Ten of the 34 sit over a rewritten history, where the packaged
commit cannot be walked back to at all. That document asked `gh` about all 38 from a
script, `docs/evidence/scripts/review_fixes_past_package.py`, because the
ledger could not answer. It stays repeatable only for as long as GitHub still
holds those branches.

**Nothing downstream re-gates the difference.** The merge train of `DESIGN.md`
§6.1 is what would re-run the full gate suite on the merged result. Item 97
records that the train is not built, and the documented path stays `gh pr
ready` and then `gh pr merge`. Until the train exists, the commit a spec's work
merged at is a fact no artifact holds.

**§4.2.1 bars a column of a different kind.** `DESIGN.md:408` calls a column
written at scan and read by nobody item 18's pattern wearing a schema. Its
subject is `tasks.priority`. That value is read once at
scan, to sort a list already in memory, and the spec file yields it again on
any later night. The head a pull request merged at is observable once, by the
scan that sees the merge, and is gone when the branch is deleted. A column
holding it keeps a measurement nothing else can make later, and that is the
distinction §4.2.1 rests on. The same line says when the reader arrives: "It
gets added the first night something reads it back." Here the reader is item
97's other open half, the re-gate, or §6.1's merge train. Neither can be built
without the head this column holds, so the column is what unblocks the reader
rather than what waits on it.

**The ledger section of `DESIGN.md` needs no edit.** §4.1 is `protected`. Its
`tasks` tuple at `DESIGN.md:305-307` already omits `pushed_sha` and `pr_url`,
both of which `saffron/ledger.py:73-74` declares. A column missing from that
block is the existing shape rather than a contradiction to resolve. This
change makes the third such column, not the first.

**What `SA-0099` settles, and what it does not.** The line quoted under "Out of
scope" is about deferring the *reader*. That is the half this spec leans on.
`runs.preflight` was already named in `DESIGN.md:303-304` and declared at
`saffron/ledger.py:58`. So `SA-0099` wrote a column §4.1 had declared. This
spec adds one §4.1 does not name. `pushed_sha` and `pr_url` are the precedent
for that second half, not `SA-0099`. Put both halves in the pull request body,
separately.

## Problem

- **The row that becomes `MERGED` keeps no trace of the head it merged at.**
  The task's gate results, findings and rebuttal describe the cell's diff. The
  pull request merged a different tree in 34 of 38 cases. The ledger records
  the state change alone.
- **Printed is not recorded.** One line on the terminal of whichever command
  ran the scan is the whole artifact. `saffron batch` runs that scan overnight
  with nobody reading.
- **There is one chance to take it.** A `MERGED` row leaves
  `PR_PENDING_STATES`, the branch is deleted, and `gh pr view` starts erroring
  on it. The answer sits in hand at `saffron/reconcile.py:158` and is discarded
  four lines later.
- **The measurement cannot be repeated.** The only account of this defect is a
  one-off script against a GitHub that still held the branches.

## Out of scope

**The re-gate.** Running the task's gates, from the same `base_sha` export,
over the new head is item 97's other open half. It is a larger change, because
it needs a `Tree` for a tree that is not a running cell's. `saffron/gates/**`
and `saffron/cell/**` are `forbidden` here. Record the head. Judge nothing.

**A reader for the column.** `saffron/cli.py`, `saffron/report/**`,
`saffron/chain_walk.py` and `saffron/projection.py` are all `forbidden`.
The reader is the re-gate above, or the merge train
of §6.1, and neither exists yet. `SA-0099` set the precedent at
`.saffron/specs/done/SA-0099-runs-preflight-is-a-column-nothing-writes.md:139`,
in its own words: "A written column with no reader beats a reader inventing
one."

Say in the pull request body why §4.2.1 allows this one, in the Context
section's terms. Say there too that the guard at `tests/test_ledger.py:802-826`
is narrower than its name. It asserts that `batches` holds no `concurrency`
and `tasks` no `priority`, and it reaches nothing else.

**Changing the printed lines.** `_print_reconcile_summary` already prints a
moved head, and `saffron/cli.py` is `forbidden`. Add no line, and leave the
one that is there alone.

**Backfilling the rows that are already `MERGED`.** Every existing row stays
without a head. A value invented for a merge nobody observed is the failure
`DESIGN.md` §4.1 names in its own words: "A column named for a measurement it
cannot make is how an estimate becomes a fact."

**Recording a non-merging pull request's head.** An open pull request is
asked again on the next scan. Its head is never lost, and `HeadMoved` already
reports it. A write on that path would reach the rows
`reconcile` leaves alone by design. It would also put a merged commit's name
on a row that was closed unmerged. The module docstring at
`saffron/reconcile.py:9-13` is about how careful its writer half has to be.
Merges only, and criterion 2's witness holds you to it.

**Widening what `reconcile` asks GitHub for.** `_pr_status` already requests
`headRefOid`. Ask for nothing further. A fourth field is a different spec.

**`DESIGN.md` and `CONTEXT.md`.** Both are `protected` and both are
`forbidden`. This spec coins no term. It stores a commit sha in a column beside
`pushed_sha`, and it introduces no new state, gate, or closed set.

## Notes for the agent

**This change is new code.** Every criterion declares a witness and no
mutant. No existing text pins honestly, because the column, the write and the
method do not exist. Nothing in the tree determines their spelling. Expect the
`witness` gate to report `skip`, with a summary saying the spec declares no
mutants. The names of the column and of the ledger method are yours to pick.

**The witnesses read the column through `ledger._db`.** The writer is the only
method this change adds. `tasks_by_repo` at `saffron/ledger.py:361-376`
selects six columns by name, and the new one will not be among them, so no test
can reach it that way. Do not add a getter beside the writer either. `dead`
blocks at `.saffron/policy.yaml:28`, `tests/` is not scanned
(`.saffron/gates/dead.py:4-5`), every would-be production reader is out of scope
above, and this spec declares no `pending_symbols`. A reader method is dead code
the day it lands. The shape to copy is in the tree twice already:
`tests/test_reconcile.py:43-46`'s `_state` helper and `tests/test_ledger.py:797`
both `SELECT` the column they are checking.

**The tier is elevated, so `size` blocks.** The `elevate_on` list in
`.saffron/policy.yaml` names `saffron/ledger.py`. This task therefore runs at
`elevated`, where the `size` gate blocks at the `bug` ceiling of 300 changed
lines. The shape asked for here is about 30 lines of source and three tests.
`SA-0099` made a comparable ledger change in 150 lines. Do not go looking for
more to do.

**Do not wedge the new column between `pushed_sha` and `pr_url`.**
`tests/test_ledger.py:278` builds an older schema with a literal
`SCHEMA.replace` over those two lines together. The line under it asserts
that the result no longer contains `pushed_sha`, "otherwise this test proves
nothing". A column inserted between the two makes that replacement match
nothing, and the assertion fails. The end of the `tasks` table is free.
`saffron/ledger.py:78` is the last column there and ends without a comma, so
the new line adds one after it.

**`CREATE TABLE IF NOT EXISTS` does not alter an existing table.** What reaches
`~/.saffron/ledger.db` is the guarded additive `ALTER TABLE` loop at
`saffron/ledger.py:179-187`. Its own comment states the rule: additive only,
never a migration that can lose a row. A column added to `SCHEMA` alone is the
plausible wrong implementation criterion 3 exists to kill. It passes on a fresh
`tmp_path` database and fails on every ledger that already exists.
`tests/test_ledger.py:1325-1342` and `:273-298` are two existing shapes for
building such a database. Copy whichever fits.

**Write the head before the state moves.** A `MERGED` row sits outside
`PR_PENDING_STATES` and is never asked again. A write that lands after the
state change is one crash away from being lost for good. Two statements in that
order are fine, and so is one statement doing both. Add it as a new writer
method, or as a keyword on `set_task_state` that defaults to writing nothing.
Never as a required parameter. That signature has thirteen callers in
`saffron/cell/session.py` and one in `saffron/replay.py`, both `forbidden`.
Nine test files outside `touches` call it too. The state first is the one order
that is wrong.

**Criterion 1 has three plausible wrong implementations.** All three come from
the `HeadMoved` branch at `saffron/reconcile.py:159`, which sits right there and
is the easy read. The first records the head only where it differs from
`pushed_sha`. The second records `pushed_sha` itself rather than the head the
answer carried. The third copies that branch's guard whole, `isinstance(head,
str) and head and pushed`, so it writes nothing for a merged row whose
`pushed_sha` is NULL. That row shape is not hypothetical:
`tests/test_reconcile.py:253` already drives it under the id
`no-push-recorded`. The witness must drive three merges in one
plain `def`: one head differing from the packaged commit, one equal to it, and
one on a row with no packaged commit at all. Assert the stored value against the
head in each case. Do not reach for `pytest.mark.parametrize`. `criteria`
matches a bare node id against the names the suite collected, by exact string.
A parametrised test collects under a name no criterion can name.

**Criterion 2 has three plausible wrong implementations.** The first is a
fallback. A `head or pushed`, or a `str(head)`, turns an unanswered question
into a confident commit. An empty string is the case that catches a bare
`isinstance(head, str)` guard, and `tests/test_reconcile.py:246-263` already
pins it for `HeadMoved` at `:251` and `:258`. Absence of an answer is never
recorded as an answer in this module. The comment at
`saffron/reconcile.py:95-98` says so for its state writes. The second wrong
implementation writes the head beside every state move rather than beside the
merge. `_next_state` at `saffron/reconcile.py:118-131` returns `REJECTED` and
`CHANGES_REQUESTED` down the same path, and the head is in hand there too. The
third is that one narrowed to the two states this module already treats alike:
`new_state in ("MERGED", "REJECTED")`. It is the reading the comment at
`saffron/reconcile.py:45-47` invites. `REJECTED` leaves `PR_PENDING_STATES` at
`saffron/reconcile.py:48` on the same "asked for the last time" argument this
spec makes for `MERGED`. It is also the one wrong implementation a witness
whose only non-merge is `CHANGES_REQUESTED` leaves alive. What it does is put a
merged commit's name on a row that was closed unmerged. So the witness drives
five answers in one plain `def`. Three are
merges, with the field absent, empty, and a non-string. The fourth moves a row
to `CHANGES_REQUESTED` and the fifth moves one to `REJECTED`, each over a real
head that differs from `pushed_sha`. Each leaves the column as it was.
Criterion 2 on its own is satisfied by recording nothing at all. Criterion 1 is
what makes it a real constraint, so both witnesses have to hold at once.

**One comment in the tree becomes false.** It is the only prose this change
owes. The comment on the `head_moved` field at `saffron/reconcile.py:100-101`
reads "Reported, never written", and it describes a module that wrote no sha.
Rewrite that one run in place and in two lines: say that the merge path now
writes a head, and that `head_moved` itself is still only reported. Edit no
other comment. The module docstring at `saffron/reconcile.py:9-13` is about the
reader and writer asymmetry over *state*, and it stays true as it stands.
`prose` blocks here and counts comment runs per file, so a third line in that
run is an uncancelled failure and a repair turn. The same holds for any comment
run this change adds to `saffron/ledger.py`, which already carries a seven-line
run at `:291-297`: two lines there as well.

**Rename no existing test, and suppress nothing.** `census` compares the set
of collected test names between base and head. A rename reads as a removal. The
block from `tests/test_reconcile.py:192` onwards is item 97's own. The new
tests belong with it.

**Import anything new inside the test body.** `tests/test_reconcile.py:13`
imports from `saffron.reconcile` at module scope, and every name there exists
at base. A module-scope import of a name this change adds turns the reverted
run of `revert` into a collection error. `revert` reads that error as `skip`,
and the anti-theater gate then checks nothing.

Commit after each coherent step. Uncommitted work dies with the cell.
