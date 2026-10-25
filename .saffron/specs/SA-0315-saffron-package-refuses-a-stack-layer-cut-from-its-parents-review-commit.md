---
id: SA-0315
title: "`saffron package` refuses a stack layer cut from its parent's review commit, since only a parent's `pushed_sha` counts"
type: feature
priority: 2
depends_on: [SA-0313]
estimated_lines: 280
estimate_measured: true
touches:
  - saffron/task.py
  - tests/test_task.py
  - tests/test_cli.py
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
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 180
risk: standard
acceptance:
  - claim: >-
      `ready_task` takes a keyword `mirror_path`. When no task's
      `pushed_sha` equals the tree base, it falls back to origin's
      branches. A task qualifies when its `pushed_sha` is an ancestor of
      the tree base and its branch head, fetched from origin, is the tree
      base or descends from it. The newest qualifying task's branch is
      `parent_branch`. The witness drives a tree base one commit above
      the parent's `pushed_sha` and a tree base equal to the branch head.
      Every branch commit reaches origin from a second clone, so the
      checkout and the mirror lack it until a fetch. Four decoys stand
      beside the parent. A newer task's branch carries the tree base, but
      its `pushed_sha` is off the tree base's history. A newer task's
      `pushed_sha` is an ancestor, but its branch does not carry the tree
      base. A newer task's `pushed_sha` is its own branch head, a commit
      above the tree base. An older task qualifies too.
    witness: tests/test_task.py::test_ready_task_stacks_on_the_newest_branch_that_carries_its_tree_base_above_a_pushed_sha
    wrong_versions:
      - The fallback picks the newest task whose branch carries the tree base and never checks its `pushed_sha`.
      - The fallback picks the newest task whose `pushed_sha` is an ancestor and never reads its branch.
      - The fallback picks the oldest qualifying task.
      - The fallback accepts only a tree base equal to the branch head.
      - The fallback accepts only a tree base strictly below the branch head.
      - The fallback checks that the `pushed_sha` is an ancestor of the branch head rather than of the tree base.
      - The fallback never fetches. It takes each head from `ls-remote` and runs `merge-base` in the mirror.
      - The fallback refuses at once when the mirror does not hold the tree base.
      - The fallback reads `refs/remotes/origin/<branch>` in the mirror rather than fetching from origin.
  - claim: >-
      A tree base that no task's branch at origin carries is still refused.
      The reason names its first twelve characters and says no branch at
      origin carries it. The `tasks` table is left as it was. A task whose branch origin lacks is skipped, never
      raised on. The witness drives four such tree bases. Each has a task
      that records the branch named below, with the parent's `pushed_sha`.
      One sits on a branch only the checkout holds, which the mirror copies
      from the checkout. One sits on the checkout's own copy of an origin
      branch, ahead of where origin's copy stops. One sits on a branch
      origin held, which the checkout fetched and origin then deleted. One
      is a sha no repository holds. When the checkout's `origin` url names
      a path that does not exist, `ready_task` raises rather than refusing.
    witness: tests/test_task.py::test_ready_task_refuses_a_tree_base_no_branch_at_origin_carries
    wrong_versions:
      - The fallback reads a task's branch from the mirror's own `refs/heads`, which `ensure_mirror` copied from the checkout, not from origin.
      - The fallback reads `refs/remotes/origin/<branch>` in the mirror, which still names a branch origin deleted.
      - The fallback fetches every task's branch without listing origin first, so a branch origin lacks raises `ParentGone` out of `ready_task`.
      - The fallback skips the `rev-parse --verify` step, so a sha no repository holds raises from `git merge-base` with exit 128.
      - The fallback skips `ls-remote`, fetches each task's branch and catches `ParentGone` as a skip.
      - The fallback reads a failed `ls-remote` as an empty list.
  - claim: >-
      Every refusal `ready_task` made before the fallback returns before
      any mirror step. The witness names `mirror_path` and `repo` at paths
      that do not exist. It drives each refusal it drove at base, the
      unmatched tree base excepted, and checks that `mirror_path` still
      does not exist after each. Its `spec_sha` case writes a tree base
      that differs from `base_sha` and that no task pushed.
    witness: tests/test_task.py::test_ready_task_refuses_with_a_reason_and_writes_nothing
    preserves: true
  - claim: >-
      A tree base equal to a task's `pushed_sha` still stacks on that
      task's branch with no mirror step. The witness names `mirror_path`
      and `repo` at paths that do not exist.
    witness: tests/test_task.py::test_ready_task_stacks_on_the_branch_of_the_task_that_pushed_its_tree_base
    preserves: true
  - claim: >-
      A tree base equal to `base_sha` still rebuilds every field with no
      mirror step. The witness names `mirror_path` and `repo` at paths that
      do not exist.
    witness: tests/test_task.py::test_ready_task_rebuilds_every_field_package_reads_from_the_cells_record
    preserves: true
  - claim: >-
      `saffron package` hands `ready_task` the same mirror path it later
      hands `prepare_mirror`.
    witness: tests/test_cli.py::test_package_probes_the_host_then_runs_package_on_the_rebuilt_task
    preserves: true
---

## Context

Backlog item **b-066901**, under `DESIGN.md` §5.7. It is the half of that
item `SA-0313` leaves. `SA-0313` (b-619b7d) has `saffron adopt` record a
pull request's head as the task's `pushed_sha`. `SA-0316` has a batch exit
2 when PACKAGE raised, and leaves the task for `saffron package`. This spec
lets `saffron package` take a stack layer cut from a parent's review commit.

Every line below was read at `af2831e8`. `SA-0313` edits
`tests/test_cli.py` before this spec runs, so find each test there by name.

**A stack layer's tree base is its parent's branch head.** `DESIGN.md`
§5.7 says `tree_base` is "the parent's branch head for a stacked one"
(`DESIGN.md:1283`). The spec loop pushes review commits early, so that head
is often a review commit and no task's `pushed_sha`. In run 46, `SA-0302`'s
PACKAGE raised during re-verification. `saffron package SA-0302` then
refused with "076bf182097f was pushed by no task in this repo".

**`ready_task` matches the tree base exactly.** When `tree_base` differs
from `base_sha`, it keeps the rows of `ledger.tasks_by_repo` whose
`pushed_sha` equals `tree_base`. With none, it returns that refusal.
Otherwise the newest wins, and its branch is read off
`ledger.tasks_by_spec_id`, since `tasks_by_repo` carries no `branch`
column. That exact match is `saffron/task.py:989-998`, its branch read
`:999-1008`, and the columns `saffron/ledger.py:1147-1152`. The refusals
before it come at `:905-933`, and `_spec_for_task` refuses an unmatched
`spec_sha` at `:939-941`.

**The rebuild runs no git and touches no disk.** Its docstring says
nothing in it writes, to the ledger or to disk (`saffron/task.py:897-899`).
Its signature takes `spec_id`, `repo`, `repo_id`, `ledger` and `out_dir`
(`saffron/task.py:889-896`).

**`package_ready_task` already holds the mirror path.** It takes
`mirror_path` (`saffron/task.py:1223-1232`). It calls `ready_task` first,
returns a `Refused` untouched, and only then calls
`preflight.prepare_mirror(repo, mirror_path)` (`:1242-1248`). Its docstring
says a `Refused` comes back "before the mirror, the image or the network
exist" (`:1236-1237`). `saffron package` builds `mirror_path` with
`_mirror_path(repo, args.home)` and hands it over (`saffron/cli.py:2937-2946`).

**The mirror alone cannot answer.** `ensure_mirror` clones a new mirror
from the checkout with `--mirror --no-local`, which copies every ref,
`refs/remotes/*` included (`saffron/repos/mirror.py:84-92`). It fetches an
existing mirror from the checkout with `--prune` (`:74-81`).
A branch the checkout lacks is deleted from the mirror, and a branch the
checkout holds is the checkout's copy, not origin's. §5.7 says the same
of the mirror and the working copy. So the tree base can be missing from the
mirror until a branch is fetched from origin.
`package_phase.fetch_parent_branch(mirror, url, branch)` fetches one branch
from origin into the mirror. It raises `ParentGone` when origin lacks it
(`saffron/phases/package.py:167-196`). `package_phase.real_remote(repo)`
gives origin's url (`:97-104`).

**The tests.**
- `tests/test_task.py` calls `ready_task` 15 times, none with a mirror.
- `test_ready_task_refuses_with_a_reason_and_writes_nothing` drives every
  refusal (`tests/test_task.py:2915-3059`). Its last case is an unmatched
  tree base, `"e" * 40`, with `repo` at a path that does not exist
  (`:3035-3057`). Its `spec_sha` case writes `tree_base` equal to
  `base_sha` (`:3025`), so the fallback condition never holds there.
- The `_rt_*` helpers write ledger rows and files only (`:2460-2560`).
  `_git` and `_commit` build real git (`:967-990`).
- `test_package_probes_the_host_then_runs_package_on_the_rebuilt_task`
  replaces `ready_task` with `fake_ready_task(spec_id, *, repo, repo_id,
  ledger, out_dir)` (`tests/test_cli.py:3735-3737`). It checks the first
  call's arguments at `:3841`.

## Problem

1. **`ready_task` takes `mirror_path`.** It is a required keyword. It is
   read only on the fallback below.
2. **The fallback.** Two conditions start it. The `tree_base` differs
   from `base_sha`, and no task's `pushed_sha` equals it. The exact match keeps its
   current behaviour.
   - Origin's url comes from `package_phase.real_remote(repo)`, and the
     mirror from `ensure_mirror(repo, mirror_path)`.
   - A qualifying task has a `pushed_sha` and a `branch`. Its
     `pushed_sha` is an ancestor of the tree base. Its branch head,
     fetched from origin, is the tree base or descends from it.
   - The newest qualifying task wins, and its branch is `parent_branch`.
   - A branch origin lacks disqualifies its task. A sha the mirror does
     not hold as a commit disqualifies too.
   - A failed `git ls-remote` raises, and so does a failed fetch of a
     branch it listed. Neither is a refusal, since `saffron package` exits
     1 on a refusal and 2 on infrastructure. A branch `ls-remote` listed
     that is gone by its fetch raises too, as infrastructure.
   - With none qualifying, the refusal names the tree base's first twelve
     characters. It says the tree base was pushed by no task in this repo,
     and no branch at origin carries it.
3. **Every other refusal stays ahead of the mirror.** No-task, state,
   pull request, file, `spec_sha` and the exact match all return before
   the fallback runs.
4. **Docstrings.** The docstrings of `ready_task` and `package_ready_task`
   name the one path that reads the mirror. `ready_task`'s stays within
   ten lines, the prose gate's cap.
5. **Existing tests.**
   - Every `ready_task` call in `tests/test_task.py` passes `mirror_path`.
     The three `preserves` witnesses name one under `tmp_path` that does
     not exist and assert it is still absent afterward.
   - The unmatched `"e" * 40` case moves out of the refusal test into
     criterion 2's witness, since it now reaches the fallback.
   - The refusal test's `spec_sha` case writes a `tree_base` such as
     `"d" * 40`, so a fallback hoisted above `_spec_for_task` reaches the
     mirror there and fails.
   - `fake_ready_task` in `tests/test_cli.py` accepts `mirror_path` and
     records it. The test asserts it equals the path `prepare_mirror` got.

## Out of scope

- `saffron adopt` (`SA-0313`).
- A batch's exit code, and offering a raised PACKAGE again (`SA-0316`).
- `saffron package` for a task not in `READY_FOR_REVIEW`.
- Any change to how PACKAGE itself fetches a parent (`saffron/phases/`).
- `ledger.py`. Read a task's branch the way `ready_task` does now.

## Notes for the agent

The fallback is new code, so criteria 1 and 2 declare a witness and no
mutant. Criteria 3 to 6 are `preserves` witnesses that exist at base. Each
one gains `mirror_path` in this change.

**Fetch little.** Measured off base, in the home ledger on 2026-10-23: 262
tasks carry a pushed sha, 248 of them `MERGED`, and most of their branches
are deleted. List origin's
branches once with `git ls-remote <url> 'refs/heads/*'`. Keep only tasks
whose branch origin still has. Walk those newest first and fetch each with
`fetch_parent_branch`. Stop at the first that qualifies. Fetch before the
ancestry checks, since the tree base can be missing from the mirror until
then (`ensure_mirror --prune`, `saffron/repos/mirror.py:74-81`).

**Mirror `_pushed_landed`** (`saffron/cli.py:515-541`). Check each sha first
with `git rev-parse --verify --quiet <sha>^{commit}`. Exit 1 means the
mirror lacks it, which disqualifies the task, and any other failure raises.
Then run `git merge-base --is-ancestor`. Exit 0 qualifies, exit 1
disqualifies, and any other exit raises. So a sha no repository holds
is refused, never raised on. A failure of `ensure_mirror`, `real_remote`,
`ls-remote` or a listed branch's fetch still raises. That is infrastructure, and
`saffron package` exits 2 on it.

**The fixture for criteria 1 and 2.** Build it from `_git` and `_commit`
(`tests/test_task.py:967-990`). Keep `_rt_ledger`, `_rt_task`,
`_rt_write_patch` and `_rt_seed_records` for the ledger and task directory.
- Make a bare `origin.git` and a checkout whose `origin` remote is its path.
  `ensure_mirror` clones the checkout, and `real_remote` reads its remote.
- In the checkout, commit `B` on `main` and push it. The checkout holds
  nothing else in criterion 1.
- In a second clone of `origin.git`, commit `P`, the review commit `R`,
  `R2` and `R3` in a line. Commit `X` on `main` after `B`. Push each
  branch from there, so the mirror lacks these commits until it fetches.
  Origin's `saffron/RT-2` sits at `R2`. `R3` reaches origin only as
  `saffron/RT-8`.
- A decoy's branch can point origin at an existing commit, such as
  `git push origin <R2>:refs/heads/saffron/RT-3`.
- For criterion 2, the checkout fetches origin first. The checkout-only
  branch and the checkout's own `saffron/RT-2` each take a commit above
  `P` that origin never receives. The deleted branch is pushed from the
  second clone, fetched by the checkout, then removed inside `origin.git`
  with `git update-ref -d`.
- For the raise, point the checkout's `origin` at a path that does not
  exist with `git remote set-url`, after the refusal cases.
- Record `pushed_sha` and `branch` with `ledger.set_task_package`, as
  `test_ready_task_stacks_on_the_branch_of_the_task_that_pushed_its_tree_base`
  does.
- Create tasks oldest first. `tasks_by_repo` orders by `task_id`.

**Kill the wrong versions with the arrangement.** In criterion 1, the
parent `RT-2` records `P`. The newer decoys must all lose to it:
- `RT-3` records `X`, and its origin branch sits at `R2`.
- `RT-4` records `P`, and its origin branch stops at `P`.
- `RT-8` records `R3`, and its origin branch sits at `R3`.
The older `RT-5` records `B`, and its origin branch sits at `R2`. A
prototype of this fixture killed every wrong version listed under
criteria 1 and 2.
