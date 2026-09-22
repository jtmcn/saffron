---
id: SA-0124
title: The diff stat PACKAGE measures reaches `queue.json` and no ledger column, so nothing the index could be rebuilt from holds it
type: feature
priority: 2
depends_on: [SA-0123]
touches:
  - saffron/ledger.py
  - saffron/phases/package.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/record/**
  - saffron/report/**
  - saffron/cell/**
  - saffron/repos/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/replay.py
  - saffron/reconcile.py
  - saffron/projection.py
  - saffron/chain_walk.py
  - tests/test_report.py
  - tests/test_fold.py
  - tests/test_spec_loop_driver.py
budget_usd: 24
max_attempts: 3
max_turns: 150
risk: elevated
acceptance:
  - claim: >-
      Each of the four PACKAGE paths that return after `diff_stat` ran writes
      the stat it measured to the task's row. On `READY_FOR_REVIEW` a
      measured 0 reads 0 rather than NULL. The four
      are new failures on re-verification, a credential in the pull request
      body, a branch that moved under the lease, and `READY_FOR_REVIEW`. The
      witness drives all four in turn on one `packageable` task, whose diff
      adds 2 lines and removes 1. It then drives `READY_FOR_REVIEW` a second
      time over a patch that adds one empty file, which measures 0 and 0.
      Before each of the five `package()` calls it writes 7 and 7 into the row's two
      columns through a `sqlite3` connection of its own. After each it asserts
      the path's own note or state. It reads 2 and 1 through `queue_lines`
      after the first four, and 0 and 0 after the fifth. Today
      `set_task_package` takes no stat and `tasks` has no column for one.
    witness: tests/test_package.py::test_every_package_path_that_measured_the_diff_records_its_stat
  - claim: >-
      Each of the four PACKAGE paths that return before `diff_stat` ran writes
      NULL to both columns, never 0. The four are a parent branch that is
      gone, a patch that conflicts, a credential in the patch, and a credential
      in an agent commit subject. The witness drives all four in turn on one
      `packageable` task, writing 7 and 7 into the row before each as
      criterion 1 does. After each it asserts the path's own note, reads NULL
      for both through `queue_lines`, and reads 0 and 0 from the task's line
      in `queue.json`. Today `PackageResult` defaults both counts to 0, and
      that 0 reaches the queue line as though it were measured.
    witness: tests/test_package.py::test_every_package_path_that_returned_before_the_diff_was_measured_records_no_stat
  - claim: >-
      `set_task_package` puts the stat in its `task_package` fact as payload
      keys `added` and `removed`, each `None` where the caller passed none.
      The fold rebuilds both columns from that payload, and a `task_package`
      fact carrying neither key folds to NULL. The witness writes six tasks
      through a ledger with a record attached. One is packaged with 2 and 1,
      one with 0 and 0, and one with no stat. One is never packaged. One is
      packaged with 5 and 5 and then again with no stat. The last is packaged
      with 5 and 5, and the witness then strips both keys from that fact. The
      first task's fact carries 2 and 1, and the never-packaged task has no
      `task_package` fact. After a fold into a fresh ledger, both ledgers read
      2 and 1, then 0 and 0, then NULL for the next three. The fresh ledger
      reads NULL for the stripped task.
    witness: tests/test_ledger_fold_task.py::test_the_diff_stat_folds_back_as_written_and_null_where_unmeasured
  - claim: >-
      A ledger file whose `tasks` table lacks both columns opens with both
      added and NULL in each row it held. The witness builds the file from
      `SCHEMA` with the two columns' lines removed, and asserts the removal
      changed the text. The file holds two tasks, and both read NULL through
      `queue_lines` after the open. A `set_task_package` with 3 and 4 on the
      first task then reads back 3 and 4 through a second `Ledger` on the same
      file, and the second task still reads NULL.
    witness: tests/test_ledger.py::test_a_ledger_that_predates_the_diff_stat_gains_it_as_null
  - claim: >-
      Each task fact kind still folds back to the rows its write made, column
      for column but the ids and timestamps, with no column of the final
      snapshot NULL but `findings.adjudication`.
    witness: tests/test_ledger_fold_task.py::test_every_task_fact_kind_folds_back_to_the_rows_its_write_made
    preserves: true
  - claim: >-
      A green cell still becomes a draft pull request whose body and index
      line both carry its diff stat, 2 lines added and 1 removed.
    witness: tests/test_package.py::test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line
    preserves: true
---

## Context

Backlog item **171**, the half of item 170 a cell can land. `DESIGN.md` §6
names the defect at `DESIGN.md:1221`: the diff stat its own mock shows "is
stored in no column at all". §5.7 is the phase that measures it.

This spec is `SA-0123`'s child. `SA-0123` routes every ledger write method
through `Ledger._apply`. Each method builds its fact, applies it, commits
once, and then appends it. Write this change against that shape. The line
numbers below were read at this spec's base, `cbb63af3`, before `SA-0123`
landed. Those in `saffron/ledger.py`, `tests/test_ledger.py` and
`tests/test_ledger_fold_task.py` move before a cell runs, since `SA-0123`
edits all three.

What the code does today:

- PACKAGE measures the stat once, at `saffron/phases/package.py:792`:
  `added, removed = mirror_ops.diff_stat(mirror, target_head, pushed)`.
- `PackageResult` declares both counts with a default of 0, at
  `saffron/phases/package.py:585-586`.
- `package()` returns through `_finish` on eight paths. Four return before
  `:792`, and none of them passes a stat. They are the gone parent
  (`:691-698`), the conflict (`:736-747`), and `_refuse` for the patch
  (`:767`) and for the commit subjects (`:774`). Four return after `:792`,
  and each passes `added=added, removed=removed`. They are the new failures
  (`:840-854`), `_refuse` for the body (`:887`), the lease rejection
  (`:901-915`) and `READY_FOR_REVIEW` (`:929-944`).
- `_finish` (`saffron/phases/package.py:955-984`) calls
  `ledger.set_task_package` with state, branch, pushed sha and URL at
  `:959-965`, and no stat. It hands `result.added` and `result.removed` to
  the `QueueLine` at `:975-976`.
- A `PackageError` raised out of `package()` reaches neither write, by design
  (`_finish`'s docstring, `:956-958`).
- `set_task_package` (`saffron/ledger.py:1135-1165`) writes four columns and
  appends a `task_package` fact whose payload holds those four.
  `_apply`'s `task_package` branch (`saffron/ledger.py:581-593`) reads the
  same four back.
- `tasks` (`saffron/ledger.py:75-97`) has no column for the stat.
  `queue_lines` (`saffron/ledger.py:1293-1304`) selects ten named columns.
- `QueueLine` declares the pair at `saffron/report/index.py:60-61`, and the
  index renders it at `:175`. `queue.json` and the pull request body hold
  it, and no ledger column does.
- The ledger adds a column to an existing file with a guarded `ALTER TABLE`,
  at `saffron/ledger.py:214-234`. The loop at `:221-230` adds `TEXT`
  columns. `spent_usd_est` gets its own guarded statement at `:231-234`
  because its type differs.

## Problem

Delete `queue.json` and the counts are gone, though every commit that produced
them survives. No record the index could be rebuilt from holds them.

A stored 0 cannot stand in for "not measured". `DESIGN.md` §4.1 says why,
at `DESIGN.md:337`. Its last sentence names a column that claims a
measurement it cannot make. A `MERGE_FAILED` task whose patch conflicted has
no diff to count. Today its queue line reads `+0/−0`, which is also what an empty diff reads.

The change:

1. **`tasks` gains two nullable `INTEGER` columns, `added` and `removed`.**
   An existing ledger file gains them through the guarded `ALTER TABLE` that
   `saffron/ledger.py:214-234` already uses. A row that held no stat keeps
   NULL.
2. **`set_task_package` takes the stat** as two keyword-only parameters,
   `added` and `removed`, each `int | None` and defaulting to `None`. Its
   `task_package` fact carries both in its payload, `None` included.
   `_apply`'s `task_package` branch writes both columns from the payload.
   A payload without the keys writes NULL. After `SA-0123` that branch is
   the one place either ledger writes the columns.
3. **`PackageResult` defaults both counts to `None`.** The four paths that
   measured still pass theirs. `_finish` passes the pair to
   `set_task_package` as it stands. It passes 0 for a `None` count to the
   `QueueLine`, so `queue.json` and the index read as they do today.
4. **`queue_lines` selects both columns**, so the ledger has a reader for
   what it now holds.

A task that never reaches `_finish` keeps NULL, since nothing writes to its
columns. That covers a task that never reached PACKAGE and one whose PACKAGE
raised.

## Out of scope

**Rendering the index from the ledger or the record.** The index keeps
rendering from `queue.json`. Making it render from the authoritative record is
item 170, which is `by_hand`. So item 171 closes `partial`: the record holds
the stat, and the page still reads it from the file.

**`QueueLine` and `queue.json`.** `saffron/report/**` is `forbidden`. A
`QueueLine` keeps `int` counts, and an unmeasured path still writes 0 there.
Telling the two apart on the page is item 170's call.

**`DESIGN.md`.** §6's clause at `DESIGN.md:1221` becomes half false: the stat
is now stored in a column, and the page still does not read it. `DESIGN.md`
is `protected`. Item 170 rewrites that paragraph. §4.1's `tasks` tuple at
`DESIGN.md:305-307` already omits `pushed_sha`, `pr_url` and
`merged_head_sha`, so two more omitted columns need no edit there.

**A new fact kind or vocabulary.** The payload of an existing kind gains two
keys. `KINDS` in `saffron/record/contract.py:19-38` is unchanged, and
`CONTEXT.md`'s fact kind entry lists kinds, not payloads.

**Backfilling a stat for rows that exist.** No row's diff can be re-measured
from the ledger. NULL is the honest value, per §4.1's sentence above.

**`replay.py`.** v0's replay measures its own stat into a `QueueLine`
(`saffron/replay.py:49`). It writes a task row (`:55`) but never calls
`set_task_package`, so its columns stay NULL. Leave it.

## Notes for the agent

**This change is new code.** The columns, the two parameters and the payload
keys do not exist at base. So every criterion not marked `preserves`
declares a witness and no mutant, and `witness` reports `skip`. That skip is
honest.

**Commit as each witness passes.** A long cell can reach its turn limit before
its first commit.

**Where the stat lands after `SA-0123`.** `set_task_package` builds one
`task_package` fact and applies it through `_apply`. Put the two keys in that
fact's payload, and have `_apply`'s branch read them with `payload.get`. Do
not write the columns with SQL of their own in `set_task_package`. That is
the two-writer shape `SA-0123` removes.

**The migration.** Copy the shape at `saffron/ledger.py:231-234`, one guarded
`ALTER TABLE ... INTEGER` per column. The loop at `:221-230` spells `TEXT`.
Place the two lines in `SCHEMA` after `prompt_sha`. Keep them off the pair
`tests/test_ledger.py:278` removes with one literal, and above
`merged_head_sha`. The comment below `merged_head_sha` at
`saffron/ledger.py:92-96` records why a comment must not sit above the last
column.

**Criteria 1 and 2 build on the `packageable` fixture**
(`tests/test_package.py:857-962`). Its diff is +2/−1 on purpose, as its
comment at `:894` says. Criterion 1's witness makes five runs and criterion
2's makes four. Each witness is one plain `def` that drives its paths in
turn on one task, and resets the fixture's changes between them.
The seed of 7 and 7 before each path is what makes each path's own write
visible. Without it, a write that kept the old value would pass on every
path after the first. Write the seed through a `sqlite3` connection opened
on `tmp_path / "l.db"`, the file the fixture's ledger uses. Read the result
through `_state` (`tests/test_package.py:964`), which reads `queue_lines`.
Assert each path's note or state first, so a path that fell through to
another is caught.

A prototype of both witnesses was run at this base. How each path was
reached:

- New failures: the existing `reverify` stub, returning one `NewFailure`
  (as `tests/test_package.py:1401-1430` does). Note `new failures
  re-verifying`.
- Body credential: `outcome.reviews` with one finding whose claim holds
  `FAKE_KEY` (as `tests/test_package.py:1561-1597` does). Note
  `credential in the body`.
- Lease: push `cell` to the remote's `saffron/SA-0005`, and stub
  `remote_sha` to return `""` (as `tests/test_package.py:1303-1330`
  does). Restore the real `remote_sha` after it. Note `moved underneath us`.
- `READY_FOR_REVIEW`: a `gh` stub printing a pull request URL.
- Commit subject: `outcome.agent_subjects` holding `FAKE_KEY`.
- Patch: commit a file holding `FAKE_KEY` on `cell` in the fixture's work
  tree, and rewrite `patch.diff` from it (as
  `tests/test_package.py:1492-1524` does). Restore the patch after it.
- Gone parent: `patch.json`'s `tree_base` set to the `cell` commit, which the
  mirror holds and `main` does not reach. Pass
  `parent_branch="saffron/SA-0020"`, a branch the remote never had. Restore
  `patch.json` after it.
- Conflict, last: push a commit to `main` that rewrites line 3 of `f.txt`.

**Criterion 1's fifth run is a measured 0.** A `_finish` that passed
`result.added or None` would store NULL for an empty diff. Two runs on the
prototype tested it.

- A patch that only changes `f.txt`'s mode does not reach `diff_stat`. It has
  mode headers and no hunk, so `apply_patch` raises `PackageError`: "git
  fell back to direct application: the preimage blob is absent".
- A patch that adds one empty file does reach it. Build it on a branch cut
  from the fixture's base, and rewrite `patch.diff` from it. Its header carries
  `index 0000000..e69de29`. PACKAGE reached `READY_FOR_REVIEW` with the
  result's counts at 0 and 0, and the row read 0 and 0. Both runs used the
  host's git. In `saffron/cell-base:python`, git 2.39.5 applied the same
  empty-file patch with `git apply --3way --index` and exited 0. Its stderr
  held only "Falling back to direct application...", never
  `_NO_BLOB`'s text, so `apply_patch` returns `APPLY_OK` there too.

The `or None` counterfeit passed the witnesses of criteria 1 to 4 without
the fifth run
(`4 passed`). With the fifth run, criterion 1's witness failed it. Run the
fifth after the four, reusing the `gh` stub. The lease then reads the branch
the fourth run pushed.

The prototype's counterfeits and what they did. Defaulting `PackageResult`
to 0 failed criterion 2. Dropping the stat from the lease path failed
criterion 1. `COALESCE` in the column write failed criteria 2 and 3.
Passing `None` through to the `QueueLine` failed criterion 2. A `_finish`
passing `or None` to `set_task_package` failed criterion 1's fifth run. A fold that
defaulted a missing key to 0, wrote `or None`, indexed the payload, or dropped
the pair failed criterion 3. So did a writer that left the keys out. Adding
the columns to `SCHEMA` alone failed criterion 4. Each witness failed with the
source reverted.

**Criterion 3's cases each stand for a wrong implementation.** The 0 and 0
task fails a fold that writes `payload.get(...) or None`. The task packaged
twice fails a write that keeps the old value. The stripped task fails a fold
that defaults a missing key to 0, and one that indexes the payload for
them. The first
task fails a writer that leaves the keys out of the payload. Strip the keys
the way `_retimed` (`tests/test_ledger_fold_task.py:397-403`) rewrites facts,
with `dataclasses.replace`. Read rows through `_raw_rows` (`:43`), never
through `ledger._db`.

**Criterion 4's witness copies `tests/test_ledger.py:273-298`.** Assert
`before != SCHEMA`, as `:1194` does, so a literal that matches nothing fails.

**One test's body changes, and keeps its name.** Criterion 5's witness ends
with a loop. It asserts that no column of the final snapshot is NULL but
`findings.adjudication` (`tests/test_ledger_fold_task.py:206-211`). The new
columns are NULL unless its `set_task_package` call passes a stat. So pass one
there (a prototype passed 6 and 2), wherever `SA-0123` leaves that call.
`census` fails a test that disappears, so rename nothing.

**Callers that need nothing.** The defaults keep every other
`set_task_package` call valid: `tests/test_fold.py:72`,
`tests/test_ledger.py:196` and `:295`, `tests/test_spec_loop_driver.py:797`,
and `docs/evidence/scripts/2026-09-20-fold-rebuild-time.py:94`. No call
passes the stat positionally. `tests/test_cli.py` and `tests/test_task.py`
build a `PackageResult` without counts and never read them. Leave all of
these alone.

**Import nothing at module scope that this change adds.** `revert` runs the
new tests with the source reverted. An import of a new name is then a
collection error, which it reads as `skip`. `tests/test_package.py` needs
`sqlite3` for the seed. That import is fine, since the standard library holds
it at base.

**Size.** A prototype of this change at this base measured 278 changed lines
after `ruff format`, before docstrings. It spent 21 in `saffron/ledger.py`,
11 in `saffron/phases/package.py`, 142 in `tests/test_package.py`, 72 in
`tests/test_ledger_fold_task.py` and 32 in `tests/test_ledger.py`. Expect
about 330 with docstrings. The `feature` ceiling is 600, and `size` blocks
at `elevated`, which `saffron/ledger.py` makes this task.

**Prose.** Each touched file's `prose` count must not rise. New comments and
docstrings take no em-dash, semicolon, contraction, perfect tense or hedge.
Keep a docstring within ten lines and a comment within two. Check each file
with `python3 hooks/prose_limit.py --file <path>`.
