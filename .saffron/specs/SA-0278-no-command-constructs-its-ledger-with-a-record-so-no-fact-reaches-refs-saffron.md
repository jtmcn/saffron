---
id: SA-0278
title: "No command constructs its `Ledger` with a record, so no fact a night writes reaches `refs/saffron/*`"
type: feature
priority: 1
depends_on: [SA-0268, SA-0265, SA-0260]
estimated_lines: 490
estimate_measured: true
touches:
  - saffron/record/routed.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/repos/mirror.py
  - saffron/events.py
  - tests/test_record_routed.py
  - tests/test_task_record.py
  - tests/test_cli.py
  - tests/test_mirror.py
  - CLAUDE.md
  - docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/backlog/**
  - docs/evidence/**
  - docs/appendices/**
  - docs/adr/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/record/contract.py
  - saffron/record/refs.py
  - saffron/record/memory.py
  - saffron/record/fold.py
  - saffron/record/migrate.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/replay.py
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/view/**
  - saffron/report/**
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/test_record_refs.py
budget_usd: 45
max_attempts: 3
max_turns: 210
risk: elevated
acceptance:
  - claim: >-
      A `Ledger` built with `RoutedRecord(lambda key: ledger.record_home(key))`
      files each fact it appends on its task's ref in the mirror of the repo
      that task ran against, and in no other mirror. That holds for two repos
      that share one `repos.name` and differ in origin and mirror. The witness
      writes a `task_created` and a `task_state` fact for each task and reads
      both mirrors with `RefsRecord`.
    witness: tests/test_record_routed.py::test_each_fact_lands_in_the_mirror_of_the_repo_its_task_ran_against
    wrong_versions:
      - A version that resolves a fact by its `repo` name and takes the first `repos` row of that name.
      - A version that caches one `RefsRecord` for the first mirror it resolves and reuses it for every task.
      - A version whose cache is keyed by repo name, so two mirrors of one name share one record.
  - claim: >-
      `Ledger.push_record(task_id)` on a ledger with a `RoutedRecord` pushes
      that task's ref to the origin of the task's own repo, and the origin
      then reads the same facts as the mirror. An append pushes nothing: the
      origin holds no task ref until `push_record` runs. Another repo's origin
      in the same ledger stays empty.
    witness: tests/test_record_routed.py::test_a_push_carries_the_whole_ref_to_the_tasks_origin_and_an_append_pushes_nothing
    wrong_versions:
      - A version whose `append` also pushes, as a `RefsRecord` given a remote does.
      - A version that pushes to the origin of the most recently upserted repo.
  - claim: >-
      `push_record` on a ledger built with no record, or with a
      `MemoryRecord`, returns without pushing or raising, even when the task's
      repo row names a mirror and an origin that do not exist.
    witness: tests/test_record_routed.py::test_a_ledger_without_a_routed_record_pushes_nothing
    wrong_versions:
      - A version that builds a `RefsRecord` from `record_home` and pushes whatever record the ledger holds.
  - claim: >-
      `run_task` pushes the task's record exactly once, after PACKAGE's last
      fact, on every way out of it that follows a returned cell. The witness
      drives five: a packaged `READY_FOR_REVIEW`, an `EXHAUSTED` cell packaged
      in the exhausted mode, an `EXHAUSTED` cell PACKAGE never ran on, a
      `PackageError` from a `READY_FOR_REVIEW` cell's PACKAGE, and a
      `RuntimeError` from it. In each case a fake PACKAGE, or a fake push of
      unpackaged work, writes a `task_push` fact. After each, the origin reads
      the mirror's facts and ends with the fact written last.
    witness: tests/test_task_record.py::test_every_way_out_of_a_task_after_its_cell_pushes_its_record_once
    wrong_versions:
      - A version that pushes right after `run_one_cell` returns, before PACKAGE.
      - A version that pushes just before the final `return outcome`, so neither raise pushes.
      - A version that pushes only when the cell ended `READY_FOR_REVIEW`.
      - A version that pushes from `set_task_state` on each state outside `IN_FLIGHT_STATES`.
      - A version that pushes on the return path and again in a `finally`.
  - claim: >-
      A push `run_task` cannot make leaves the task's outcome as it was. Its
      state is unchanged, `run_task` returns it, and a raise out of PACKAGE
      still propagates as itself. The task's `events.jsonl` gains one
      `Teardown` event with `ok` false whose detail carries the push error's
      message, which names the origin. The witness drives an origin path that
      is no repository, an origin whose ref for the key holds another history,
      and the first under a `PackageError`.
    witness: tests/test_task_record.py::test_a_refused_push_is_an_event_and_the_task_keeps_its_outcome
    wrong_versions:
      - A version that catches `StaleWriter` alone, so a missing remote raises.
      - A version that prints the refusal and emits no event.
      - A version that lets the push error propagate.
      - A version whose event detail is a fixed string without the error's message.
  - claim: >-
      The `Ledger` that `saffron`'s commands share is built with a
      `RoutedRecord`. The witness drives `saffron reconcile`: the `task_state`
      it writes for a seeded task lands on that task's ref in the mirror its
      repo row names.
    witness: tests/test_cli.py::test_a_command_files_each_fact_it_writes_in_the_tasks_own_mirror
    wrong_versions:
      - A version whose `main` constructs the shared ledger with no record.
  - claim: >-
      `ensure_mirror`'s fetch of an existing mirror neither prunes nor
      overwrites a ref under `refs/saffron/`. A ref the checkout lacks
      survives, and one the checkout holds at another commit keeps the
      mirror's commit. A branch the checkout deleted is still pruned, and a
      branch it gained is still fetched.
    witness: tests/test_mirror.py::test_a_mirror_fetch_neither_prunes_nor_overwrites_the_records_refs
    wrong_versions:
      - A version that keeps the plain `+refs/*:refs/*` fetch with `--prune`.
      - A version that drops `--prune` and keeps the forced `+refs/*:refs/*` refspec.
      - A version that adds the negative refspec and drops `--prune`.
---

## Context

Backlog item **170**, its design step 3's successor. It cites `DESIGN.md`
§4.1, §4.4, §4.6 and §6. Every line number below was read at `bc879e2c`.

**The record is built, and nothing production writes to it.** `Ledger`
takes one optional `Record` (`saffron/ledger.py:388-389`). `_append`
hands each fact to it after the commit that wrote the row, and catches
nothing (`saffron/ledger.py:590-601`). The ledger's own docstring says no
caller constructs one with a record (`saffron/ledger.py:3-9`). The
`"migrate"` and `"serve"` commands return before the shared ledger exists
(`saffron/cli.py:254-266`). The rest share `Ledger(args.home / "ledger.db")`,
which takes no record (`saffron/cli.py:268`). The fold command builds its
own, `Ledger(Path(args.into))` (`saffron/cli.py:2082`).

**A `RefsRecord` is one repository.** It takes one repo path and an
optional remote (`saffron/record/refs.py:28-31`). Given a remote, `append`
pushes after every fact (`saffron/record/refs.py:55-75`). `push(task_key,
remote)` pushes one task's ref, and a non-fast-forward raises `StaleWriter`
(`saffron/record/refs.py:88-113`). Both are `RecordError`s
(`saffron/record/contract.py:55-69`).

**A fact names its repo by `repos.name`, which is not unique.**
`_build_fact` reads `r.name` through the task's run
(`saffron/ledger.py:569-588`). `repos.origin` is `UNIQUE` and `name` is
not (`saffron/ledger.py:87-88`). The replay path calls
`ledger.upsert_repo(name, str(repo_dir), str(mirror), policy_sha)`, with the
checkout's path as origin (`saffron/replay.py:53`). So its row can share a
name with the real row. A task's own row is reached through
`tasks.run_id` and `runs.repo_id`, and carries `mirror_path` and `origin`.
`upsert_repo` sets both on every call (`saffron/ledger.py:999-1019`).
A cell upserts its row with `str(mirror)` (`saffron/cell/session.py:1960`).
The stack mint and the draft command pass `str(pinned.mirror)`
(`saffron/cli.py:1119-1121`, `saffron/cli.py:1265-1267`).

**The mirror prunes what the checkout lacks.** `ensure_mirror` fetches
`+refs/*:refs/*` with `--prune` from the operator's checkout
(`saffron/repos/mirror.py:69-73`). The checkout holds no `refs/saffron/*`,
so each fetch deletes every task ref in the mirror. Measured on
2026-10-11 under git 2.54.0 on the host and 2.47.3 in
`saffron/cell-base:python`: a plain mirror fetch deleted a local
`refs/saffron/tasks/k1`, and the same fetch with `^refs/saffron/*` added
kept it. `prepare_mirror` runs that fetch before `saffron cell` creates its
task (`saffron/preflight.py:422-439`, `saffron/cli.py:504-506`). The
queue's resolver calls `git_mirror.ensure_mirror` unless a batch pinned the
mirror (`saffron/cli.py:1534-1541`).

**A cell still cannot reach the record.** The seed fetches
`+refs/heads/*:refs/remotes/origin/*` alone and removes the remote
(`saffron/cell/worktree.py:66-73`). The spike measured that a mirror
holding `refs/saffron/tasks/*` gives a cell neither the ref nor its objects
(`docs/evidence/2026-09-17-state-on-git-refs.md:31-62`).

**Where a task ends.** `run_task` calls `run_one_cell` and re-raises
anything it raises (`saffron/task.py:601-628`). After it returns, a
`READY_FOR_REVIEW` cell or an `EXHAUSTED` one with a standing blocker
reaches `package()` (`saffron/task.py:630-669`). A `PackageError` from a
`READY_FOR_REVIEW` cell's PACKAGE writes `READY_FOR_REVIEW` and re-raises,
as any other raise does (`saffron/task.py:654-668`). Every other cell
reaches `push_unpackaged_work` (`saffron/task.py:715-752`). The function
returns at `saffron/task.py:753`. `Teardown` carries `step`, `ok` and
`detail` (`saffron/events.py:365-378`), and `describe` renders it as
`teardown:` and its detail (`saffron/events.py:896-899`).

**The design leaves the push to the wiring.** No production path sets a
remote, and the retry lands with the wiring
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:165-170`).

**The design's §8 rule waits on it too.** Every append is to emit an
event. The rule binds once a production caller constructs a `Ledger` with
a record (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:363-367`).

## Problem

Wire the record in. Every fact a command writes lands locally on its
task's ref in that task's repo mirror. `run_task` pushes the task's ref
once, as the task ends. A push it cannot make is an event in the task's
log and never the task's outcome.

**`saffron/record/routed.py` holds `RoutedRecord`.** Its constructor takes
one callable. It maps a task key to the mirror path and the origin of the
repo that task ran against. `append(task_key, fact)` checks the fact is
filed under its own key, then appends through a `RefsRecord` for that
mirror, built with no remote. It keeps one `RefsRecord` per mirror path.
`read(task_key)` reads through the same record. `push(task_key)` pushes
the key's ref to its origin. `task_keys` and `compare_and_swap` raise a
`RecordError` naming why a routed record cannot answer: the fold reads
each repo's own `RefsRecord`, and §10 of the record design gives values
their home.

**`saffron/ledger.py` gains two methods.** `record_home(key)` returns the
mirror path and origin of the repo row the task's run names, joined on
`tasks.record_key`. It raises a `RecordError` for a key no task holds.
`push_record(task_id)` returns at once unless the ledger's record is a
`RoutedRecord`. Otherwise it pushes the task's key through it. Rewrite
the module docstring's second paragraph (`saffron/ledger.py:3-9`). It
says the commands construct the ledger with a routed record. The ledger is
still written directly and read for state. The batch and run folds are the
later work.

**`saffron/cli.py:268`** builds the shared ledger with
`record=RoutedRecord(lambda key: ledger.record_home(key))`. The lambda
reads `ledger` only when a write appends, after the name is bound.

**`run_task`** calls `ledger.push_record(outcome.task_id)` once, after
`run_one_cell` returns, on every way out that follows: both returns and
every raise. A `try` around everything after the cell returns, with the
push in its `finally`, does that. It catches `RecordError` from the push
and emits a `Teardown` with `ok` false whose detail carries the error's
message. It never changes `outcome.state` and never replaces an exception
already propagating. A raise out of `run_one_cell` pushes nothing: the task
never ended, and it stays in flight until a scan stamps it.

**`ensure_mirror`** adds the negative refspec `^refs/saffron/*` to its
fetch of an existing mirror, so the fetch neither prunes nor overwrites the
record's refs. A comment of one or two lines says why.

**The tests this breaks.** A local append raises when a task's mirror is no
repository, as `_append` lets any record error do today. Eight tests in
`tests/test_cli.py` seed a mirror path that does not exist and drive a
command that writes a fact. They are
`test_reconcile_writes_what_gh_says_or_withholds_when_it_cannot_answer`,
`test_queue_reconciles_before_it_scans_so_the_refusal_gate_sees_current_state`,
`test_queue_schedules_a_task_reconcile_moved_into_a_requeue_state`,
`test_each_stack_layers_threshold_agrees_with_what_run_stack_batch_admits`,
`test_the_batch_scan_orphans_the_queue_row_of_each_task_it_stamps`,
`test_a_stack_batch_writes_its_stack_view_into_the_queue_page`,
`test_saffron_draft_writes_the_last_recorded_text_and_exits_by_how_the_draft_ended`
and
`test_saffron_draft_numbers_its_spec_past_the_working_tree_its_retirees_and_this_repos_tasks`.
Their mirrors come from `_seed_repo`'s `"/m.git"` (`tests/test_cli.py:1971-1972`),
`"/m.git"` in the stack helpers' own `upsert_repo` calls, and
`_readiness_passes`'s `/tmp/pinned-mirror.git` (`tests/test_cli.py:3427-3445`).
Give each a bare repository under `tmp_path` instead, through optional
parameters on those helpers, and leave every other caller's arguments as
they are.

**The documentation, as cell work.**

- `saffron/events.py:365-371`: `Teardown`'s docstring names a refused
  record push beside the cell's own teardown facts.
- `CLAUDE.md:138-144`: the `saffron/record/` bullet names `routed.py` and
  says every command's `Ledger` carries one. That replaces the sentence
  saying nothing constructs a record-backed ledger yet.
- The record design's §3
  (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:165-170`).
  The wiring appends into each task's mirror with no remote. The task's ref
  is pushed once as the task ends, a refused push is an event, and nothing
  re-reads or retries.
- Its §4
  (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:243-248`).
  Every command now constructs its ledger with a routed record.
- Its §8
  (`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md:363-367`).
  This wiring does not build the rule, and the ledger's append still emits
  no event.

## Out of scope

- **Design step 4**, the batch and run folds, with `batch.py`'s budget read
  from the fold rather than `ledger.batch_spend`. A later spec.
- **Design step 5**, `queue.json` as a render of the record and its
  equality check. A later spec.
- **§8's event-per-append rule.** `_append` emits nothing, and this spec
  leaves it so.
- **Facts a task gains after `run_task`.** `reconcile` writes `MERGED` and
  the other review states into the mirror and pushes nothing. They reach the
  origin with the task's next push, if it has one.
- **A retry, or a re-read of the remote.** A mirror can lack a task's ref.
  The task then appends a fresh history, and its push is refused as stale.
  A mirror made fresh, or one for another checkout path, does this. The
  refusal is the event above.
- **`saffron/phases/package.py:8-11`** says any ref the checkout lacks is
  deleted on the next fetch. After this spec that holds for every ref
  outside `refs/saffron/`. That file is forbidden here.
- **Protected text.** The operator writes `DESIGN.md` §4.6, §6 and §10 and
  `CONTEXT.md` §8's **Ledger** entry by hand, in the commit that adds this
  spec.

## Notes for the agent

**Every criterion is new code.** `RoutedRecord`, `record_home` and
`push_record` do not exist at base. The push in `run_task` and the
mirror's refspec are new lines. So each criterion declares a witness and no
mutant, and `witness` reports `skip` for each.

**Imports.** Import `RoutedRecord` inside each test body or helper, never at
a witness module's top. The reverted run would then be a collection error,
which `revert` reads as `skip`.

**Git in the witnesses.** Every repository is a `git init --bare` under
`tmp_path`, and every origin is a local path. Each new test sets `HOME` and
`XDG_CONFIG_HOME` to an empty directory under `tmp_path` and sets
`GIT_CONFIG_NOSYSTEM`, so no user or system config reaches a push.

**The fakes in criteria 4 and 5.** Replace `task_module.run_one_cell`,
`package_phase.package` and `package_phase.push_unpackaged_work`. By default
none of these writes a fact. A test whose fake PACKAGE writes nothing passes
a version that pushes before PACKAGE, since the origin and the mirror then
agree. So each fake PACKAGE and each fake `push_unpackaged_work` writes a
`task_push` fact through the ledger, with distinct shas, before it returns
or raises. Count pushes with a spy on `RoutedRecord.push`, set once per test
rather than once per case.

**The stale origin in criterion 5.** Create a second task on a second
routed ledger whose origin is the stale repository. Copy that task's ref in
its mirror to `refs/saffron/tasks/<first key>`, and push it to the stale
origin. The first task's push is then not a fast-forward.

**Criterion 6.** Seed the repo row and task through a plain `Ledger` before
`cli.main` runs, so the mirror holds only what the command wrote. Use
`_fake_gh_says_merged` (`tests/test_cli.py:2003-2006`). Every other command
but `migrate`, `serve` and `fold` shares the same ledger, so the witness
drives one command for all of them.

**Criterion 7.** In the checkout, delete the `feature` branch and add one
before the second `ensure_mirror`, beside the two task refs.

**Wrong versions.** Each criterion lists the ones its witness must kill. A
prototype's witnesses killed all 19 on 2026-10-11, failed with the source
reverted, and passed with the change. Do not run them yourself.

**The `prose` gate** counts every new comment, docstring and Markdown line.
Write none with an em dash, a semicolon, a contraction, the perfect tense or
a sentence over 25 words.

**Size.** `saffron/ledger.py` is in `elevate_on`, so the task is `elevated`
and `size` blocks. The prototype held every source change, all seven
witnesses, the eight repaired tests and the documentation. It measured 1963
tokens with `size`'s own counter against the `feature` ceiling of 3000.
Source was 612 of them, tests 1205, and documentation 146.
`estimated_lines` is that count over four.
