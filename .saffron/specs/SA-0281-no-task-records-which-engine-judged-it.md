---
id: SA-0281
title: No task records which engine judged it, so two engines' results read alike in the ledger
type: feature
priority: 2
depends_on: [SA-0280, SA-0262, SA-0264, SA-0271]
estimated_lines: 337
estimate_measured: true
touches:
  - saffron/engine.py
  - saffron/ledger.py
  - saffron/cell/session.py
  - saffron/phases/package.py
  - saffron/report/pr_body.py
  - tests/test_engine.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_session.py
  - tests/test_report.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .gitignore
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
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/report/index.py
  - saffron/view/**
  - saffron/gates/**
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 40
max_attempts: 3
max_turns: 200
risk: elevated
acceptance:
  - claim: >-
      `engine_commit(source)` in a new `saffron/engine.py` returns the text of
      a file named `ENGINE_COMMIT` in the directory `source`, stripped of
      surrounding whitespace, when that text is not empty. It does so whether
      or not a checkout holds `source`, and before it asks git anything. A
      blank file reads as no file. The witness drives a baked file inside a
      committed checkout and one in a directory no checkout holds. It drives
      two blank files inside the checkout, an empty one and one holding only
      a newline, a space and a newline. Each blank one reads the checkout's
      `HEAD`.
    witness: tests/test_engine.py::test_a_baked_engine_commit_is_read_before_any_checkout
    wrong_versions:
      - A version that asks git first and reads the file only when no checkout answers.
      - A version that returns the file's text without stripping it.
      - A version that returns an empty string for a blank file.
      - A version that reads the file raw and returns its stripped text whenever the raw text is not empty.
  - claim: >-
      With no baked value, `engine_commit(source)` returns the full
      40-character `HEAD` of the checkout whose top level is the parent of
      `source`. It appends `-dirty` when a tracked file differs from `HEAD`,
      staged or not. An untracked file marks nothing. It never writes the
      checkout's index. The witness drives a clean checkout whose tracked
      file's mtime moved forward, and asserts the index bytes are unchanged. It
      then drives the same checkout with only an untracked file added, then
      with an unstaged edit to a tracked file, then with that edit staged.
    witness: tests/test_engine.py::test_a_checkout_reports_its_head_and_marks_a_tracked_change_dirty
    wrong_versions:
      - A version that counts an untracked file as a change.
      - A version that reads only unstaged changes, so a staged edit reads clean.
      - A version that returns an abbreviated commit.
      - A version built on `git describe --always`.
      - A version that runs a plain `git status`, which rewrites the index after an mtime moves.
  - claim: >-
      `engine_commit(source)` returns `None` when there is no baked value and
      the parent of `source` is not the top level of a checkout with a
      commit. It raises nothing in those cases. The witness drives a
      directory no checkout holds, a `saffron/` directory nested below
      another checkout's top level, and a checkout with no commit.
    witness: tests/test_engine.py::test_no_baked_value_and_no_checkout_of_its_own_reads_none
    wrong_versions:
      - A version with no top-level check, so a directory nested in another checkout reads that checkout's `HEAD`.
      - A version that raises on a checkout with no commit.
      - A version that returns a placeholder string rather than `None`.
  - claim: >-
      Called with no argument, `engine_commit()` reads the directory that
      holds `saffron/engine.py`, wherever the process's working directory
      is. The witness changes the working directory to a temporary one and
      compares the call with one that names that directory.
    witness: tests/test_engine.py::test_with_no_argument_it_reads_its_own_directory_wherever_it_runs
    wrong_versions:
      - A version whose default is the `saffron` directory below the current working directory.
  - claim: >-
      `Ledger.record_engine(task_id, engine_commit)` appends a `task_engine`
      fact and sets the task's `engine_commit` column.
      `Ledger.task_engine_commit(task_id)` reads that column, and `None` for
      a task with none. The last fact written for a task wins. A fold of the
      record into a fresh ledger rebuilds the column. The witness drives
      three tasks on one record-backed ledger, one written twice, one written
      once and one never written. It reads all three live and after the fold.
    witness: tests/test_ledger.py::test_an_engine_commit_is_a_fact_the_fold_keeps
    wrong_versions:
      - A version whose write updates the column with SQL and appends no fact.
      - A version whose fold keeps the first engine written rather than the last.
      - A version whose reader ignores `task_id` and returns the newest engine on any task.
      - A version whose fold writes the engine into `policy_sha`.
  - claim: >-
      A ledger built before the `engine_commit` column gains it when opened.
      Its existing row survives, reads `None`, and takes a later write.
    witness: tests/test_ledger.py::test_a_ledger_built_before_the_engine_commit_column_gains_it
    wrong_versions:
      - A version that adds the column to the schema text alone, which an existing table never runs.
  - claim: >-
      At cell start `_drive_cell` asks `saffron.engine.engine_commit()` once,
      with no argument. It records the answer with `record_engine` when the
      answer is not `None` and differs from what the task carries. The
      witness drives five cells. A freshly minted task records the engine,
      with one `task_engine` fact. A given task recorded under another engine
      records the new one, with one fact. The same task under the same
      engine appends no fact. An engine that reads `None` appends no fact,
      so the given task keeps its engine and a fresh task reads `None`. The
      witness's fake records the arguments of every call.
    witness: tests/test_session.py::test_a_cell_records_the_engine_that_judged_its_task
    wrong_versions:
      - A version that passes the engine to `create_task` alone, so a given task keeps its old engine.
      - A version that records the engine on every cell, whatever the task carries.
      - A version that asks about the target repo's checkout rather than the engine's own directory.
      - A version that writes a `None` engine over the one on record.
  - claim: >-
      `render_pr_body` takes `engine_commit`, `None` by default. When it is
      set, the Provenance section carries a line `- engine` followed by the
      value in backticks, directly below the `head` line. When it is `None`,
      the body is the set body with that one line removed, and no line reads
      `- engine`.
    witness: tests/test_report.py::test_the_provenance_names_the_engine_commit_and_nothing_where_none
    wrong_versions:
      - A version that renders the line with `None` in it when no engine is recorded.
      - A version that puts the line after `touches` or `artifacts`.
  - claim: >-
      PACKAGE passes the engine its task carries in the ledger to
      `render_pr_body`, so `pr_body.md` names the engine that judged the
      cell. The witness records an engine on the task that no running
      process reports, and finds its line in `pr_body.md`.
    witness: tests/test_package.py::test_the_pull_request_body_names_the_engine_the_task_recorded
    wrong_versions:
      - A version where PACKAGE asks `engine_commit()` itself rather than reading the task's row.
      - A version that never passes the engine, so the body carries no line.
---

## Context

Backlog item **b-2e0b97**, tier 2. It cites `DESIGN.md` §1.4, §2 and
§5.1.2. ADR 10 frames it. Its consequences say each task records the engine
commit that judged it
(`docs/adr/0010-saffron-ships-as-an-engine-each-operator-deploys.md:115`).
The operator scoped this spec to that half on 2026-10-11. Every line number
below was read at this spec's own branch, cut from `bc879e2c`.

**A task records what it ran under, and no engine.** `tasks`
carries `policy_sha` and `prompt_sha` (`saffron/ledger.py:140-141`).
A cell writes both when it mints a task (`saffron/cell/session.py:1969-1984`).
It then writes `policy_sha` again through `record_policy` when a given task
carries another (`saffron/cell/session.py:1987-1990`). `record_policy`
appends a `task_policy` fact (`saffron/ledger.py:1546-1552`). The fold's
`task_policy` branch sets the one column (`saffron/ledger.py:845-847`).
`task_policy_sha` reads it back (`saffron/ledger.py:1536-1544`). No
column, fact or reader names the engine. On the laptop the engine and the
target are one checkout, and every `saffron cell` rebuilds its images from it
(`CLAUDE.md:43`). So two tasks judged by two engines read the same.

**This branch already carries the vocabulary.** The record's alphabet lists
`task_engine` (`saffron/record/contract.py:26`). So do `factory:FactKind`
and `CONTEXT.md`, since `KINDS` must equal `factory:FactKind`
(`tests/ontology/test_vocabulary_agrees_with_code.py:174`). For a kind with
no branch, `_apply` raises `fold cannot place fact kind`
(`saffron/ledger.py:997`). So nothing appends one until this spec lands.
`engine_commit` is in §4.1's list of task columns (`DESIGN.md:366`).
Its paragraph on `engine_commit` says what the column holds
(`DESIGN.md:412-416`).

**How the baked value travels.** The wheel is built by hatchling from
`packages = ["saffron"]` (`pyproject.toml:44-49`). Hatchling packs an
untracked file in `saffron/` that `.gitignore` does not name. Measured on
2026-10-11: `saffron/ENGINE_COMMIT` written into a clone, then
`uv build --wheel`, put the file in the wheel with its text intact. An image
that copies the tree carries it the same way. So a plain file beside
`saffron/__init__.py` reaches every install shape and needs no registry,
no `pyproject.toml` edit and no generated module.

## Problem

Record which engine judged each task, and show it on the pull request.

1. **`saffron/engine.py`** is a new module. `engine_commit(source=None)`
   reads `ENGINE_COMMIT` in `source` first. With none, it asks git about the
   checkout whose top level is the parent of `source`. `source` defaults to
   the directory holding `saffron/engine.py`.
2. **The ledger** gains a `tasks.engine_commit` column, a `task_engine` fold
   branch, a `record_engine` writer and a `task_engine_commit` reader. Each
   follows its `policy_sha` counterpart.
3. **A cell** asks the engine at start, beside the policy check. An
   answer that differs from what the task carries is recorded.
4. **PACKAGE** reads the task's engine from the ledger and hands it to
   `render_pr_body`. The body names it under Provenance, below `head`.

`policy_sha` is shown nowhere today. No module in `saffron/report/` or
`saffron/view/` names it. Its one reader, `task_policy_sha`, feeds the
comparisons that decide a rewrite (`saffron/cell/session.py:1989`,
`saffron/phases/package.py:824`). So the
pull request body is where the engine is shown, because that is the page a
task's reviewer reads.

## Out of scope

- **Building, pushing and pinning the engine image by digest**, and the
  build step that writes `saffron/ENGINE_COMMIT`. That is by hand, as infra.
  The step must write the file inside the build context, never into an
  operator's checkout, since a file left there outranks that checkout's
  `HEAD`. This spec only reads the file.
- **`saffron migrate`.** Its docstring lists the kinds it writes, ending
  at `stack_finish` (`saffron/record/migrate.py:9-15`). `task_engine` is
  not among them, so a migrated task folds with a NULL engine.
  `saffron/record/**` is `forbidden`. Live writes reach the record
  once SA-0278 lands, since it builds the production `Ledger` with a
  record. `record_engine` appends through `_append` like every other
  write. Only `saffron migrate` of a ledger written before that wiring
  drops the engine, and that stays out of scope.
- **Tasks no cell starts on.** A stack batch mints its task through
  `create_task` with no engine (`saffron/cli.py:1123`). Its cell records
  one when it starts, as a given task. The draft command's own
  `create_task` (`saffron/cli.py:1271`) mints a task that never reaches a
  cell, so it records none.
- **PACKAGE run again under another engine.** It re-verifies and writes
  `record_policy` (`saffron/phases/package.py:824-825`). It does not record
  an engine, so the task keeps the engine its cell recorded.
- **The morning queue.** `QueueLine` carries no engine
  (`saffron/report/index.py:86-112`), and the item's "the morning queue
  shows it" is left for a follow-up.
- **An untracked file** never marks a checkout dirty. A new module the
  checkout has not added therefore reads clean.

## Notes for the agent

**Every criterion is new code.** The module, the ledger methods, the cell
lines and the `render_pr_body` parameter do not exist yet. So no criterion
declares a mutant, and `witness` reports `skip` for each.

**At base every witness fails.** `saffron.engine` does not exist,
`Ledger` has no `record_engine`, and `render_pr_body` refuses
`engine_commit`. Import a new name inside the test function, never at a
witness module's top. A module-scope import makes the reverted run a
collection error, which `revert` reads as `skip`.

**Where the column goes.** Put it beside `prompt_sha`
(`saffron/ledger.py:141`), never after `merged_head_sha`. The comment below
that last column (`saffron/ledger.py:146-151`) records a SQLite 3.51.0 failure
once a comment sits above the last column. An existing ledger gains a
column only through the additive list (`saffron/ledger.py:400-410`).
Its docstring says `only one of three literals`
(`saffron/ledger.py:646`), and the new branch makes four.

**Two existing tests name every column and every kind.**
`_TASKS_COLUMN_READERS` (`tests/test_ledger.py:971`) needs an entry
mapping `engine_commit` to `saffron/ledger.py::Ledger.task_engine_commit`.
Without it `test_the_schema_adds_no_column_that_nothing_reads`
(`tests/test_ledger.py:1079`) fails. `_drive_eleven_kinds`
(`tests/test_ledger_fold_task.py:164`) writes each task fact kind once.
The test over it asserts `value is not None` for every folded column
(`tests/test_ledger_fold_task.py:234`). Add a `record_engine` call and an
`after(key)` beside its `record_policy` (`:197`).

**`engine_commit`'s git.** Run git with the parent of `source` as its
working directory. Compare `git rev-parse --show-toplevel` with that
directory with both resolved, since macOS reaches a temporary directory
through `/private`. `git rev-parse --verify HEAD` fails on a checkout with no
commit. `git --no-optional-locks status --porcelain --untracked-files=no`
prints nothing on a clean tree. Without `--no-optional-locks`, `status`
rewrites `.git/index` after a tracked file's mtime moves. That holds the
index lock in the operator's checkout. Measured 2026-10-11: plain `status`
rewrote the index and the flagged one did not. The flag also covers
criterion 4, whose call reads the real checkout. A non-zero exit, or git missing, reads as no answer and never
raises. Measured with git 2.54 on the host. That each flag also runs on
git 2.47.3, the git of the cell image's `python:3.12-slim-trixie` base,
is reasoned and not measured.

**The engine tests isolate git**, as `_isolate_git` does
(`tests/test_finish.py:31-39`). Set `HOME`, `XDG_CONFIG_HOME`,
`GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM`. Criterion 4's witness is the
exception: it reads the real checkout and writes nothing, and compares two
calls rather than a value. Where git cannot read that checkout, both calls
read `None`. It then passes, and its wrong version passes with it.

**Criterion 7's fake.** Drive the cells with `_drive`
(`tests/test_session.py:1350`), passing a `MemoryRecord` as `record`. Seed
the given task in `tmp_path / "ledger.db"` first, the file `_drive` opens
(`tests/test_session.py:1505`), under the repo `_drive` upserts.
`test_a_cell_given_a_task_runs_on_it_and_its_run_and_mints_neither` seeds
one that way (`tests/test_session.py:2944`). Replace `saffron.engine.engine_commit`
with a fake that returns the scripted answer and records its arguments.
Also set it on `saffron.cell.session` with `raising=False`, so either import
form reaches it. The fake ignores its arguments. So a cell that asked about
the target repo would get the same answer, and only the recorded arguments
catch it. Count `task_engine` facts under the task's key with `record.read`.

**Criterion 9's engine** is any value the running process does not report,
such as `"d" * 40 + "-dirty"`. Use the `packageable` fixture
(`tests/test_package.py:906`) with a `gh` that prints a URL, as
`tests/test_package.py:1222` does.

**Every other cell test** now runs the real `engine_commit`, which asks git
about the checkout. It took about 10 ms here.

**Wrong versions.** Each criterion lists the ones its witness must kill. A
prototype's witnesses killed all 26 on 2026-10-11, and every witness failed
with the source reverted.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, a hedge or a
sentence over 25 words.

**Size.** `saffron/ledger.py` and `saffron/cell/**` are in `elevate_on`, so
the task is `elevated` and `size` blocks. A prototype of the whole change
measured 1348 changed tokens with `size_gate`'s counter, against the
`feature` ceiling of 3000. It held the module, the ledger, cell, PACKAGE
and body edits, all nine witnesses, the mapping entry and the
`_drive_eleven_kinds` call. `estimated_lines` is that count over four.
