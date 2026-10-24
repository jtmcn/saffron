---
id: SA-0315
title: "`saffron package` refuses a stack layer cut from its parent's review commit, since only a parent's `pushed_sha` counts"
type: feature
priority: 2
depends_on: [SA-0313]
estimated_lines: 290
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
      Three decoys stand beside the parent. A newer task's branch carries
      the tree base, but its `pushed_sha` is off the tree base's history.
      A newer task's `pushed_sha` is an ancestor, but its branch does not
      carry the tree base. An older task qualifies too.
    witness: tests/test_task.py::test_ready_task_stacks_on_the_newest_branch_that_carries_its_tree_base_above_a_pushed_sha
    wrong_versions:
      - The fallback picks the newest task whose branch carries the tree base and never checks its `pushed_sha`.
      - The fallback picks the newest task whose `pushed_sha` is an ancestor and never reads its branch.
      - The fallback picks the oldest qualifying task.
      - The fallback accepts only a tree base equal to the branch head.
      - The fallback accepts only a tree base strictly below the branch head.
  - claim: >-
      A tree base that no task's branch at origin carries is still refused,
      and the reason names its first twelve characters. The `tasks` table
      is left as it was. The witness drives three such tree bases. One sits
      on a branch the checkout holds but origin does not, which the mirror
      copies from the checkout. One sits on a branch the checkout holds
      under the same name as an origin branch that does not carry it. One
      is a sha no repository holds. A task whose branch origin lacks is
      skipped, never raised on.
    witness: tests/test_task.py::test_ready_task_refuses_a_tree_base_no_branch_at_origin_carries
    wrong_versions:
      - The fallback reads a task's branch from the mirror's own refs, which `ensure_mirror` copied from the checkout, not from origin.
      - A branch origin lacks raises `ParentGone` out of `ready_task`.
      - A sha no repository holds raises from `git merge-base`, since its exit 128 is not read as "not carried".
      - The refusal names the parent's `pushed_sha` rather than the tree base.
  - claim: >-
      Every refusal `ready_task` made before the fallback returns before
      any mirror step. The witness names `mirror_path` and `repo` at paths
      that do not exist. It drives each refusal it drove at base, the
      unmatched tree base excepted, and checks that `mirror_path` still
      does not exist after each.
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
column. That exact match is `saffron/task.py:987-1001`, its branch read
`:999-1008`, and the columns `saffron/ledger.py:1147-1152`.

**The rebuild runs no git and touches no disk.** Its docstring says
nothing in it writes, to the ledger or to disk (`saffron/task.py:897-899`).
Its signature takes `spec_id`, `repo`, `repo_id`, `ledger` and `out_dir`
(`saffron/task.py:889-896`).

**`package_ready_task` already holds the mirror path.** It takes
`mirror_path` (`saffron/task.py:1027-1036`). It calls `ready_task` first,
returns a `Refused` untouched, and only then calls
`preflight.prepare_mirror(repo, mirror_path)` (`:1046-1052`). Its docstring
says a `Refused` comes back "before the mirror, the image or the network
exist" (`:1040-1041`). `saffron package` builds `mirror_path` with
`_mirror_path(repo, args.home)` and hands it over (`saffron/cli.py:2843-2856`).

**The mirror alone cannot answer.** `ensure_mirror` fetches an existing
mirror from the checkout with `--prune` (`saffron/repos/mirror.py:74-81`).
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
  (`:3035-3057`).
- The `_rt_*` helpers write ledger rows and files only (`:2460-2560`).
  `_git` and `_commit` build real git (`:967-990`).
- `test_package_probes_the_host_then_runs_package_on_the_rebuilt_task`
  replaces `ready_task` with `fake_ready_task(spec_id, *, repo, repo_id,
  ledger, out_dir)` (`tests/test_cli.py:2599-2603`). It checks the first
  call's arguments at `:2705`.

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
   - A branch origin lacks disqualifies its task. A sha the mirror cannot
     read disqualifies too.
   - With none qualifying, the refusal is today's, naming the tree base's
     first twelve characters.
3. **Every other refusal stays ahead of the mirror.** No-task, state,
   pull request, file, `spec_sha` and the exact match all return before
   the fallback runs.
4. **Docstrings.** The docstrings of `ready_task` and `package_ready_task`
   name the one path that reads the mirror.
5. **Existing tests.**
   - Every `ready_task` call in `tests/test_task.py` passes `mirror_path`.
     The three `preserves` witnesses name one under `tmp_path` that does
     not exist and assert it is still absent afterward.
   - The unmatched `"e" * 40` case moves out of the refusal test into
     criterion 2's witness, since it now reaches the fallback.
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

**Fetch little.** The home ledger holds 262 tasks with a pushed sha, 248 of
them `MERGED`, and their branches are mostly deleted. List origin's
branches once with `git ls-remote <url> 'refs/heads/*'`. Keep only tasks
whose branch origin still has. Walk those newest first and fetch each with
`fetch_parent_branch`. Stop at the first that qualifies. Fetch before the
ancestry checks, since the tree base can be missing from the mirror until
then (`ensure_mirror --prune`, `saffron/repos/mirror.py:74-81`).

**Read exit codes, not exceptions.** `git merge-base --is-ancestor` exits 0
for yes, 1 for no, and 128 for a commit it cannot read
(`saffron/cli.py:515-517`). Treat 1 and 128 as "does not qualify" here.
`git_mirror.has_commit` answers whether a sha is a commit and never raises
(`saffron/repos/mirror.py:285-294`). A failure of `ensure_mirror` or
`real_remote` itself still raises. That is infrastructure, and
`saffron package` exits 2 on it.

**The fixture for criteria 1 and 2.** Build it from `_git` and `_commit`
(`tests/test_task.py:967-990`). Keep `_rt_ledger`, `_rt_task`,
`_rt_write_patch` and `_rt_seed_records` for the ledger and task directory.
- Make a bare `origin.git` and a checkout whose `origin` remote is its path.
  `ensure_mirror` clones the checkout, and `real_remote` reads its remote.
- On `main`, commit `B` and push it.
- On branch `saffron/RT-2`, commit `P`, then the review commit `R`, then
  `R2`. Push the branch to origin at `R2`.
- A decoy's branch can point origin at an existing commit, such as
  `git push origin R2:refs/heads/saffron/RT-3`.
- For criterion 2, a checkout-only branch holds a commit `T` above `P`
  that origin never receives.
- Record `pushed_sha` and `branch` with `ledger.set_task_package`, as
  `test_ready_task_stacks_on_the_branch_of_the_task_that_pushed_its_tree_base`
  does.
- Create tasks oldest first. `tasks_by_repo` orders by `task_id`.

**Kill the wrong versions with the arrangement.** Criterion 1 has a newer
decoy whose branch carries `R`. Its `pushed_sha` is a sibling of `R` on
`main`, and it must lose to `RT-2`. So must the newer decoy pushed at
`P` whose origin branch stops at `P`. In criterion 2, give the
checkout's own `saffron/RT-2` a commit above `P` that origin's
`saffron/RT-2` lacks. A version that reads the mirror's ref then accepts
it, and the witness refuses.
