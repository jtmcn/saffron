---
id: SA-0224
title: A migration writes no stack rows and reaches no origin, so a ledger's history cannot become the record a second host reads
type: feature
priority: 1
depends_on: [SA-0223]
estimated_lines: 434
estimate_measured: true
touches:
  - saffron/record/migrate.py
  - saffron/record/refs.py
  - saffron/cli.py
  - tests/test_record_migrate.py
  - CLAUDE.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/ledger.py
  - saffron/repos/**
  - saffron/gates/**
  - saffron/record/__init__.py
  - saffron/record/contract.py
  - saffron/record/fold.py
  - saffron/record/memory.py
  - tests/test_fold.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
  - tests/test_ledger_fold_task.py
  - tests/test_record.py
  - tests/test_record_refs.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `migrate` also writes one fact per row of the six key-filed tables
      filed under a task's `record_key`. Those are `stack_layers`,
      `spec_reviews`, `spec_texts`, `qualifications`, `end_reviews` and
      `stack_finishes`, written as `stack_layer`, `spec_review`, `spec_text`,
      `qualification`, `end_review` and `stack_finish` facts. Each comes after
      the task's `task_state` fact and is timed at the task's `updated_at`.
      Its payload carries the columns `_apply` reads as stored, a null
      included, and a stored `n` or `position` as it is. A `stack_layer` or
      `stack_finish` fact carries its row's `batch_key`, and every other one
      the task's. Folded into a fresh ledger, the record gives back all six
      tables as multisets. A record holding each task's facts up to its
      `task_state` is completed by a rerun, with no key refused. The witness
      drives two stacked tasks, and every one of the six tables holds rows.
      There are two layers, one with a predecessor and one without. One task
      holds two spec reviews, one with every nullable column null, numbered 1
      and 3. It holds a `revision` and a `follow_up` spec text, two
      qualifications with a null `probe_verdict` at positions 1 and 3, and
      two end reviews, one with an error. The stack finish has a null
      `pr_url`. The runs move to another batch after the stack's rows are
      written, and start earlier than either task's `updated_at`.
    witness: tests/test_record_migrate.py::test_a_migrated_stack_folds_back_to_its_key_filed_rows
    wrong_versions:
      - No `spec_text` facts are written.
      - No `stack_finish` facts are written.
      - A `stack_layer` or `stack_finish` fact carries the task's batch key.
      - Every key-filed fact carries its row's `batch_key`, or null where the row has none.
      - The key-filed facts come before the task's `task_state` fact.
      - Only the first row of each table is written.
      - A key-filed fact is timed at the run's start.
      - A payload leaves out a column whose value is null.
      - A `spec_review` fact is numbered by its order among the task's facts rather than its stored `n`.
      - A `spec_review`'s `n` and a `qualification`'s `position` are numbered per task by enumerate.
  - claim: >-
      `saffron migrate --from <ledger.db>` writes each repo row's tasks, and
      only that repo's, into a `RefsRecord` on the row's `mirror_path`.
      Before it writes anything, it fetches only `refs/saffron/tasks/*` into
      each mirror from the row's `origin` URL, so the mirror's branches and
      its `refs/saffron/values/*` refs stay as they were. It then pushes each
      migrated task's ref to its own row's `origin` URL with no `--force`.
      Each ref that moves reaches the origin in one push. So a ref already
      on the origin is read and prefix-checked. One holding the start of a
      task's facts is completed, and one that disagrees is refused and left
      as it was. The command
      prints one line per task, `migrated <key>` or `refused <key>:
      <reason>`, and nothing else. It exits 1 when any task was refused, and
      never opens the home ledger. The witness drives two repo rows, each
      with a mirror cloned with `--mirror` from a third repository that holds
      a branch. The first mirror also holds a values ref. The first origin
      holds two tasks' refs from another writer, committed under another
      date. One holds the first two facts of its task, and the other one
      first fact whose `spec_sha` differs. A hook on each origin logs every
      ref it receives.
    witness: tests/test_record_migrate.py::test_migrate_writes_each_repos_tasks_to_its_own_origin_and_refuses_a_disagreeing_one
    wrong_versions:
      - Every task goes into every repo's mirror.
      - Every repo's tasks are pushed to the first repo's origin.
      - Nothing is fetched before the facts are written.
      - The mirror is fetched from its own remote named `origin`.
      - The push goes to the remote named `origin`.
      - The fetch refspec is `+refs/*:refs/*`.
      - The fetch refspec is `+refs/saffron/*:refs/saffron/*`.
      - Every append pushes, and each push failure is swallowed.
      - The command opens the home ledger before it dispatches.
      - A refused task is listed as migrated.
      - A refused task prints nothing.
      - A refusal leaves the exit code at 0.
      - A refusal raises out of the command.
  - claim: >-
      A push the origin refuses is reported per task. Git prints
      `[rejected]` for a non-fast-forward, raised as a `StaleWriter`, and
      `[remote rejected]` for a ref the origin's hook declines. That task
      prints one `push failed <key>: <class>: <reason>` line, where `<class>`
      is the exception's class. It is not listed as migrated, every other
      task still pushes, and the command exits 1. A rerun after the cause is
      gone completes the task with no fact written twice, and exits 0 when
      every task migrated and pushed. The fetch replaces a mirror ref that
      differs from the origin's and drops one the origin lacks. The witness
      drives one repo of three tasks. An origin hook declines the first
      task's ref, a `RecordError`. The origin holds another writer's first
      fact for the second task, under another date, and hides that ref from
      fetch, so the push is a `StaleWriter`. That ref is left as it was.
      Before the rerun, both causes are removed, and the mirror's ref for the
      first task gains one fact the origin never took. After it, every task's
      ref on the origin and the mirror reads as the facts `migrate` writes
      into a `MemoryRecord`.
    witness: tests/test_record_migrate.py::test_a_refused_push_is_reported_per_task_and_a_rerun_completes_it
    wrong_versions:
      - The push carries `--force`.
      - Each append pushes, as a record built with the origin as its remote.
      - Only a `StaleWriter` is reported per task, and a declined ref raises.
      - A task whose push was refused is also listed as migrated.
      - A refused push leaves the exit code at 0.
      - The push-failed reason omits the exception's class.
      - The class name in the push-failed reason is hard-coded.
      - The fetch refspec carries no `+`, so a ref that diverged is not replaced.
      - The fetch does not prune, so a ref only the mirror holds stays.
      - All of a repo's keys go in one push.
  - claim: >-
      Every repo's mirror is fetched before any fact is written. A fetch that
      fails, or a source path that does not exist, exits 2. No task ref is
      then written to any mirror or origin, and no file is created at the
      source path or at the home ledger. A push that fails with neither
      refusal, such as an origin that is gone, also exits 2. The lines the
      command printed before it are kept, since it prints each as its task
      ends. The witness drives a ledger whose second repo row names an origin
      that does not exist and shares the first row's mirror. It then drives a
      source path that does not exist. Last, it drives one repo of two tasks
      whose origin moves away after its first push, so the second push finds
      no repository.
    witness: tests/test_record_migrate.py::test_migrate_exits_two_when_infrastructure_fails_and_keeps_what_it_printed
    wrong_versions:
      - Each mirror is fetched just before its own repo's tasks are written.
      - A failed fetch is reported as a task that did not make it, so the exit is 1.
      - Every push `RecordError` is reported per task, a gone origin included.
      - The lines print only once every task has ended.
      - A repo's lines print once that repo's pushes have all ended.
      - The source is opened with a plain read-write `sqlite3.connect`.
---

## Context

Backlog item **170**, which cites `DESIGN.md` §4.1, §4.4, §4.6 and §6. Its
design is `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`.
This spec is the last of five for that design's step 3, the migration.
`SA-0220` changed the gate-result fact. `SA-0221` files a declared tier only
where a spec declared one. `SA-0222` writes the facts that fill `tasks`,
`attempts` and `findings`, and `SA-0223` adds the gate results. This spec
writes the six key-filed tables, chooses the target record per repo, pushes
it, and adds the command.

Line numbers below were read at `f692c72c`, and no cited file changed by
`fa00bd55`. That base carries `SA-0220` to `SA-0223` as queued specs, not as
code. This spec is written against their
end states. There `saffron/record/migrate.py` holds
`migrate(source, record) -> Migration`, with `migrated` and `refused`. It
opens the source read-only and compares what a key holds with the start of
its list before it appends. Its last fact for a task is `task_state`.

**What design §4 asks.** Delete the ledger, rebuild it, and get the same rows
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:250-251`).
§7 moves every stored task (`:326-327`).

§3 pushes each task's ref with no `--force`, so a refusal means a stale
writer (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:159-170`).

**Six tables are filed under a record key, not a task id.** `stack_layers`,
`end_reviews`, `qualifications`, `spec_reviews`, `spec_texts` and
`stack_finishes` each carry a `task_key` (`saffron/ledger.py:226-298`).
`_drop_task_rows` deletes all six under the key a fold rebuilds
(`saffron/ledger.py:554-565`). A fold inserts each row from its fact
(`saffron/ledger.py:776-893`). Two of them read the fact's own `batch_key`
rather than a payload field: `stack_layer` at `:785` and `stack_finish` at
`:886`. `record_stack_finish` replaces the fact's batch key with the batch it
was given (`saffron/ledger.py:1554-1580`). Every other writer takes the run's
batch through `_build_fact` (`saffron/ledger.py:512-531`).

**`task_policy` needs no fact here.** `record_policy` writes `tasks.policy_sha`
over the value `create_task` stored (`saffron/ledger.py:1450-1456`,
`:773-775`). The column holds the last one, and `SA-0222`'s `task_created`
fact carries it as stored. So the fold gives back the same column.

**What the backend can do now.** `RefsRecord(repo, remote=None)` appends
locally, and pushes after every append only when a remote is set
(`saffron/record/refs.py:28-31`, `:70-74`). `_push` runs `git push` with no
`--force` and raises `StaleWriter` where git printed `[rejected]`
(`saffron/record/refs.py:87-101`). No public method pushes one ref, and none
fetches.

**A mirror cannot push to its own remote.** `ensure_mirror` clones with
`--mirror` and refreshes with `fetch --prune origin +refs/*:refs/*`
(`saffron/repos/mirror.py:69-79`). Measured with git 2.54.0 on 2026-10-06, a
push with a refspec to such a clone's remote named `origin` fails:
`fatal: --mirror can't be combined with refspecs`. That is a `RecordError`,
not a `StaleWriter`. The same push to the origin's URL is refused as
`[rejected]` on a non-fast-forward.

**The live mirror's remote is not its repo's origin.** The real ledger has one
repo row, `wt-cell`, whose `origin` is `git@github.com:jtmcn/saffron.git`.
Its mirror's `remote.origin.url` is a local scratch checkout, read from the
mirror's `config` on 2026-10-06. So fetching or pushing by the remote's name
reaches the wrong repository, and both go to the row's `origin` URL.

**Two commits of the same facts can be one commit.** `append` builds each
commit with `commit-tree` from the fact's blob and the parent
(`saffron/record/refs.py:55-69`). Two writers appending the same facts in the
same second make the same commits, measured on the prototype. So a witness
that needs another writer's history sets `GIT_COMMITTER_DATE` for it.

**The command beside it.** `saffron fold` dispatches before the home ledger
opens, since opening it would create the file (`saffron/cli.py:228-235`). It
exits 1 when a task did not make it and 2 when infrastructure failed
(`saffron/cli.py:1779-1799`). `CLAUDE.md:65` lists it.

**Measured on a copy of `~/.saffron/ledger.db`, 2026-10-06.** 234 tasks on one
repo row. `stack_layers` holds 4 rows, `end_reviews` 10 and `spec_reviews` 5.
`qualifications`, `spec_texts` and `stack_finishes` are empty. No row of the
six names a key with no task. No `stack_layers` row's `batch_key` differs
from its task's run. 50 tasks hold a null `policy_sha`.

## Problem

1. **The six tables.** In `migrate`, after a task's `task_state` fact, write
   one fact per row of each key-filed table whose `task_key` is the task's
   `record_key`. Order the tables as `_apply` lists them, and each table's
   rows by its key column: `position`, `n`, `lens` or `batch_key`. Time each
   fact at the task's `updated_at`, as `SA-0222` times findings. Its payload
   carries the keys `_apply` reads for that kind, the stored values as they
   are. A `stack_layer` and a `stack_finish` fact take their row's
   `batch_key`, by `dataclasses.replace`.
2. **The routing.** Give `migrate` a `repo_id` keyword, `None` by default for
   every task. Given one, it migrates that repo's tasks only. `SA-0222`'s and
   `SA-0223`'s callers pass none and are unchanged.
3. **The backend.** Add `RefsRecord.push(task_key, remote)`, which calls
   `_push` for the task's ref, so a non-fast-forward keeps raising
   `StaleWriter`. Add `RefsRecord.fetch(remote)`, which runs
   `git fetch --prune <remote> +refs/saffron/tasks/*:refs/saffron/tasks/*`.
4. **The orchestration.** In `migrate.py`, read every repo row. Build one
   `RefsRecord(mirror_path)` per row, with no remote, and fetch each from its
   `origin` before anything is written. Then, per row, migrate its tasks and
   push each migrated key to that row's `origin`. Report each task as it
   ends, a generator being one way. A push `RecordError` is the task's own
   only when it is a `StaleWriter` or its `stderr` holds `[remote
   rejected]`. Report that one with the key and
   `f"{type(exc).__name__}: {exc}"` on one line. Any other push failure,
   such as a dead or missing remote, raises. So do a fetch failure and a
   failure while appending. Push each key on its own, never a repo's keys
   in one push.
5. **The command.** Add `saffron migrate --from <ledger.db>` beside `fold`,
   dispatched before the home ledger opens. Print one line per task as it
   ends: `migrated <key>`, `refused <key>: <reason>` or `push failed <key>:
   <class>: <reason>`. Exit 0 when every task migrated and pushed, and 1
   when any was refused or its push was refused. Any exception exits 2, as
   `fold`'s does, after the lines already printed. Add the command to
   `CLAUDE.md`'s list after `fold`, and to the module docstring's list in
   `saffron/cli.py`.

## Out of scope

- Renaming a repo. A fact's `repo` is `repos.name` as stored, `wt-cell` on
  the real ledger, as `SA-0222` writes it.
- Run-scoped gate results, `baseline_names`, `batches`, and a run's status
  and preflight. They are design step 4's. A rebuilt ledger still has no
  `batches` row (`saffron/record/fold.py:8-13`).
- A key-filed row whose `task_key` names no task. The fold reads a key only
  where it holds a `task_created` fact (`saffron/record/fold.py:68-80`). The
  real ledger has none.
- A retry of a refused push. The rerun is the retry. It fetches the origin's
  ref and prefix-checks it, as design §3 leaves to the caller
  (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:165-168`).
- The record being public. A push publishes each task's facts to the origin,
  the cost design §3 records
  (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:178-180`).
- A repo row whose origin is a local path, as a replay row's can be.
  `migrate` pushes to whatever `repos.origin` holds. The live ledger's only
  row names GitHub.
- `ensure_mirror` and every other path that refreshes a mirror. A cell's
  refresh still prunes a local-only `refs/saffron/*` ref, which is why this
  command pushes each task before it returns.
- Events. As `SA-0222` says, the rule that every append emits one binds once
  a production `Ledger` holds a record, and this command constructs none.
- `DESIGN.md` and `CONTEXT.md`. They are `protected`, and the hand edits this
  spec makes true are below.

## Notes for the agent

**This change is new code inside existing modules.** No text at base fixes
how it is spelled. So each criterion declares a witness and no mutant, and
the `witness` gate reports `skip` for all four. The wrong versions under each
criterion are what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Four witnesses, four commits at least.

**Every witness must fail with the source reverted.** Import
`saffron.record.migrate` inside each test, as the module's tests do. Drive
the command through `cli.main(["--home", <tmp>, "migrate", "--from", <path>])`.
At base that is an argparse exit, so each command witness fails there.

**Build each source with `Ledger`'s write methods, then close it.** Reuse the
helpers the parent cells left in `tests/test_record_migrate.py`, whatever
they named them. The names in these notes are suggestions, since no parent
spec fixes them. Make every repository a local bare one under `tmp_path`. No
test touches the network, and none reads `~/.saffron`.

**Criterion 1.** Attach both runs to one batch, then write the stack's rows,
then attach both runs to a second batch. Put both spec reviews, both spec
texts, both qualifications and both end reviews on one task. Through `_db`,
move the second spec review's `n` to 3 and the second qualification's
`position` to 3. Set the runs' `started_at` to a time before either task's
`updated_at`. Compare each table with `collections.Counter` over its row
tuples, every column included. Assert every table holds rows first. Then,
for each key, assert the six kinds are exactly the facts after `task_state`,
with its `at`, the repo's name and each `batch_key`. For the rerun, copy each
key's facts up to `task_state` through `Fact.from_json(fact.to_json())` into
a fresh `MemoryRecord`.

**Criteria 2 to 4.** Make each origin with `git init --bare`. Give a third
bare repository one commit on `refs/heads/main`, and make the mirror from it
with `git clone --mirror`. Its remote is then not the origin, as on the live
host, and it carries a branch. Write another writer's facts with a
`RefsRecord` on its own bare repository and `remote=` the origin. Set
`GIT_COMMITTER_DATE` inside `monkeypatch.context()` around that writer only,
so its commits differ from the migration's. Read the expected facts by
migrating the source into a `MemoryRecord`. Read each ref with
`RefsRecord(<bare repo>).read`. Assert the command's whole output as a
sorted list, with each line's text before its first colon exact.

**Criterion 2.** After the other writer's appends, put a `pre-receive` hook
on each origin that appends its input to a log file. Assert each migrated key
appears in its origin's log once. Every migrated ref moves in this witness. A
push of a ref the origin already holds sends nothing and runs no hook, as
measured below. So the log cannot show the refused key, and the witness
asserts that ref's sha instead. Write a values
ref into the first mirror with `compare_and_swap`, and assert it and the
branch read the same sha after the run. Assert the second origin and the
second mirror hold exactly the second repo's key, and the first origin none
of it. Assert the refused line's reason is not empty.

**Criterion 3.** Decline the first ref with a `pre-receive` hook on the
origin, an executable `sh` script that fails when its input names the key.
Hide the second ref from fetch with the origin's `uploadpack.hideRefs`.
Assert the first push-failed line starts `push failed <key>: RecordError: `
and the second `push failed <key>: StaleWriter: `. Before the rerun, delete
the hook, unset the setting, and append the first task's last fact to the
mirror's ref with `RefsRecord(mirror)`.

**Criterion 4.** For the last arm, give the origin a `post-receive` hook that
runs `mv` on the origin's own directory. The first push lands and moves it,
and the second push finds no repository. Patch no method of the code under
test. The error line spans several lines, so compare by line. Assert the
first line is the first task's `migrated` line and the second starts with
`saffron: RecordError: `.

**Git behaviours relied on, measured with the host's git 2.54.0 only.** Each
is unmeasured on the cell image's git 2.39.5.

- A push with a refspec from a `clone --mirror` to its remote by name fails
  with `fatal: --mirror can't be combined with refspecs`.
- A non-fast-forward push to a URL prints `[rejected]` with `(fetch first)`.
- A `pre-receive` hook that exits non-zero prints `[remote rejected]`.
- `uploadpack.hideRefs` hides a ref from fetch, and a push still sees it.
- A push to a path that is not a repository prints neither refusal.
- A `post-receive` hook that moves its own repository away lets that push
  exit 0. The next push to the old path exits 128 with `does not appear to
  be a git repository`.
- A push of a ref the origin already holds at that sha prints `Everything
  up-to-date` and runs no `pre-receive` hook.
- A fetch with `--prune` and a glob refspec matching nothing on the remote
  exits 0, and drops the local refs under that glob.
- `GIT_COMMITTER_DATE` changes the commit `commit-tree` makes, and two
  appends of the same facts in the same second make the same commit.

**Where the claims stop.** A failure while appending to a mirror also exits
2, after the lines already printed, and no witness drives it. A rerun
recovers through the prune. Criterion 4 drives a source path that does not
exist, not one that exists and cannot be opened. The output's order across
the three kinds is not pinned.

**What it makes true by hand.** No `DESIGN.md` or `CONTEXT.md` sentence turns
false, so no edit is required. Two optional hand edits follow from it.
`DESIGN.md` §10's layout line for `cli.py` at `DESIGN.md:1535` lists
`batch, run, queue, ratify, gc`, and names neither `fold` nor `migrate`.
`CONTEXT.md:750-752`'s **Ledger** entry names `saffron fold`, and `saffron
migrate` is the command that writes its stored tasks into the record. Design
§3's "no production path sets a remote" at
`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:166-167`
stays true, since this command pushes without setting one.

**Measured on a prototype at `f692c72c`, revised at `fa00bd55`.** The
prototype was `SA-0223`'s, with `SA-0220`'s stand-in in `saffron/ledger.py`.
On it, all four new witnesses passed, and each failed with `SA-0223`'s
module. `SA-0222`'s and `SA-0223`'s six witnesses passed on both. The change
measured 1736 changed tokens under `size_gate`. Each of the 39 wrong versions
above was applied to it as an edit, and each failed its own criterion's
witness. The `dead` gate on it reported no unused name, so this spec defers
none. Once it lands, `SA-0222`'s and `SA-0223`'s `pending_symbols` entries
for `migrate` are stale.

**Measured on a copy of the real ledger, 2026-10-06.** An earlier prototype
caught every push error per task. It migrated all 234 tasks to local bare
repositories in 1045 s, with no refusal and no failed push. The origin held
10,317 facts. A rerun took 164 s and left the same 10,317. Folded back from
the origin, the six tables matched the copy row for row.
