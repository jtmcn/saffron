---
id: SA-0131
title: A child is refused on a parent that ended `EXHAUSTED` and then merged by hand, because only a `MERGED` row counts as landed
type: bug
priority: 3
depends_on: []
touches:
  - saffron/scheduler.py
  - saffron/cli.py
  - tests/test_scheduler.py
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
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/reconcile.py
  - saffron/intake.py
  - saffron/phases/**
  - saffron/cell/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/record/**
  - tests/test_spec_loop_driver.py
  - tests/test_ledger.py
  - tests/test_batch.py
budget_usd: 18
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `build_queue` takes an optional callable that says whether a commit is
      on the default branch. Given one, a `depends_on` parent is satisfied
      when any of its task rows has a recorded pushed commit the callable
      accepts. This holds whatever state that row is in, for every state in
      `DONE_STATES` and `REQUEUE_STATES`, and for a row at a spec sha the
      parent no longer has on disk. A parent whose pushed commit the callable
      rejects, or whose rows record no push, is refused as it is today. The
      callable is asked about recorded pushed commits and nothing else. An
      exception the callable raises leaves `build_queue` unchanged, never
      read as a rejection.
    witness: tests/test_scheduler.py::test_a_parent_whose_pushed_commit_reached_the_default_branch_satisfies_its_child
  - claim: >-
      `saffron queue` answers that callable from the mirror, against the
      `base_sha` it pinned. A child is a candidate when its `EXHAUSTED`
      parent's pushed commit reached the remote's default branch through a
      merge commit, including one made on the remote that the operator's
      checkout never pulled. A child stays refused, naming `EXHAUSTED`, when
      its parent's pushed commit sits on an unmerged branch, and when the
      mirror does not hold the commit at all. The pinned `base_sha` decides,
      never a mirror ref. A pinned scan refuses the child when every mirror
      ref sits ahead of the pin at the merge, and admits it when the mirror's
      default branch sits behind the pin. Asked with a mirror git cannot
      read, the callable raises `GitError` rather than answering no, so a
      check that never ran is not reported as a refusal.
    witness: tests/test_cli.py::test_queue_admits_a_child_whose_exhausted_parent_merged_by_hand
---

## Context

Backlog item **b-111c56**, from the spec loop's run 14
(`docs/evidence/2026-09-22-spec-loop-skill-feedback-run-14.md`, point 7).
This spec is the scheduler half of that item. The spec loop driver's half is
`SA-0132`, which depends on this one.

`SA-0123` ended `EXHAUSTED`. The operator opened #451 from its branch by hand,
and #451 merged into `main` with a merge commit. The ledger row still reads
`EXHAUSTED` with no `pr_url`. `saffron queue` then refused `SA-0124`: "depends_on
SA-0123 is EXHAUSTED, which will not merge as it stands".

**How a parent counts as landed today.** `build_queue` builds
`merged_anywhere` from ledger rows in the `MERGED` state, across every spec
sha (`saffron/scheduler.py:793-797`). `_dependency_refusal` admits a parent in
that set (`saffron/scheduler.py:564-565`) or retired to `done/`
(`saffron/scheduler.py:568-569`). Otherwise a parent whose rows at its current
sha include `EXHAUSTED` or `REJECTED` is refused (`saffron/scheduler.py:608-613`).

**Why the ledger never learns of the merge.** Only `reconcile` writes
`MERGED` (`saffron/ledger.py:1082-1083`), and it skips a row with no `pr_url` or outside
`PR_PENDING_STATES` (`saffron/reconcile.py:150-151`). A hand-opened pull
request is recorded nowhere, so nothing asks GitHub about it.

**What the ledger does hold.** A task that pushed has a `pushed_sha`.
PACKAGE records it before it opens a pull request
(`saffron/phases/package.py:916-918`). When PACKAGE never runs, as for an
`EXHAUSTED` task, the push of unpackaged work records it too
(`saffron/task.py:345-351`, `saffron/phases/package.py:1176`). That
sha is always a fresh commit from `commit_squash`, which runs `git commit`
without `--allow-empty` (`saffron/phases/package.py:344-352`). So the sha is
never the base it was cut from, and it is on the default branch only once
the branch merges. `Ledger.tasks_by_repo` returns `spec_id`, `state` and
`pushed_sha` for every task in a repo (`saffron/ledger.py:712-727`).

**Measured on this repo, 2026-09-22.** `SA-0123`'s row, task 132, records
`pushed_sha` `ec7b2b9d`. `git merge-base --is-ancestor ec7b2b9d origin/main`
exits 0. #451 reads `headRefName` `saffron/SA-0123`, `baseRefName` `main`,
state `MERGED`.

**Where the queue gets its base.** `_resolve_queue` fetches the remote's
default branch into the mirror and pins its head as `base_sha`
(`saffron/cli.py:533-542`). `fetch_default_branch` force-fetches it into the
mirror's `refs/heads/<default>`, so the mirror holds commits the operator's
checkout never pulled (`saffron/phases/package.py:141-149`). The one
`build_queue` call sits after the pinned and the unpinned branches meet
(`saffron/cli.py:567-583`). `saffron batch` reaches it through the same
function, for its opening scan and its rescans (`saffron/cli.py:788-790`,
`saffron/cli.py:812-814`).

PACKAGE already asks the same question of a parent branch: it runs
`merge-base --is-ancestor` in the mirror and reads exit 0 as landed
(`saffron/phases/package.py:680-685`).

## Problem

A parent whose work reached the default branch leaves its child refused
whenever the parent's task ended in a state other than `MERGED`. The child
waits forever, because nothing will ever write `MERGED` for that task. The
only way out today is to retire the parent's spec to `done/` by hand, or to
start the child with `saffron cell`. That command applies no `depends_on`
refusal. `saffron/cli.py` calls `build_queue` once, inside `_resolve_queue`
(`saffron/cli.py:567`).

A child cut from `base_sha` is correct in this case. `task._resolve_stacked_on`
stacks only on a parent row in `DEPENDENCY_WAITING_STATES`
(`saffron/task.py:181-185`). So a child of an `EXHAUSTED` parent is cut from
the default branch, where the parent's work now is.

## Out of scope

**A squash merge and a rebase merge.** Either writes new commits. The
recorded `pushed_sha` is then not an ancestor of the default branch, and the
child stays refused with today's reason. PACKAGE carries the same limit for a
stacked parent (`saffron/phases/package.py:677-679`). The operator's way out
is unchanged: retire the parent's spec to `done/`. This repo allows all three
merge methods. #451 merged with a merge commit. Run 13's #433 merged into
`saffron/SA-0122` instead, and its task 128's `pushed_sha` `e8605e92` is not
an ancestor of `origin/main`, measured 2026-09-22. That shape stays refused.

**The spec loop driver.** `driver.py next` holds a child back on its parent's
order row, and `driver.py snapshot` calls `build_queue` without the new
callable (`.claude/skills/run-saffron-spec-loop/driver.py:198-206`). Both are
`SA-0132`'s. `.claude/**` is forbidden here.

**The ledger's state.** The task stays `EXHAUSTED`. The scheduler reads the
merge from git, and no row is rewritten.

**`DESIGN.md`.** §4.2.1 names two admissions for a landed parent, a
`MERGED` task and a retired spec (`DESIGN.md:390`). This adds a third. The
operator edits that paragraph by hand after this merges.

**The refusal text.** A parent the callable rejects keeps today's reason word
for word.

## Notes for the agent

**The change is new code.** So both criteria declare a witness and no
mutant. The callable is a new keyword on `build_queue`. Nothing at base has
text a mutant could pin for it.

**The keyword.** Add it to `build_queue` after `markers`, defaulting to
`None`. `None` means nothing is asked, and the queue is exactly today's. Every
existing call passes none, so every existing test pins that. Say what the
keyword is in `build_queue`'s docstring, beside `markers`, in the same shape
but without that paragraph's em-dash, which the `prose` gate counts.
Update the module docstring's list where it says a `depends_on` is satisfied
only by a `MERGED` task (`saffron/scheduler.py:10`).

**Where it folds in.** Add the specs whose recorded push lands to
`merged_anywhere`, after it is built at `saffron/scheduler.py:793-797`. Read the
rows from `ledger.tasks_by_repo(repo_id)`, which carries `pushed_sha`.
`tasks_by_spec` does not carry it, and `saffron/ledger.py` is forbidden. Read
every row, across every spec sha and every state. Pass the callable only a
non-empty `pushed_sha`. Each push costs two git calls on every scan.
So asking only about parents that some spec's `depends_on` names is allowed.
Skip those already in `merged_anywhere` too. Leave `_dependency_refusal` unchanged: a spec in
`merged_anywhere` already returns `None` there.

**The callable `saffron queue` passes.** Write it in `saffron/cli.py` beside
`_retirement_markers_at`, taking the mirror and `base_sha`. It asks git two
questions in the mirror. `git merge-base --is-ancestor` alone cannot tell a
missing commit from an unreadable mirror, because both exit 128.

1. `git rev-parse --verify --quiet <sha>^{commit}`. Exit 1 means the mirror
   lacks the commit, so return `False`.
2. `git merge-base --is-ancestor <sha> <base_sha>`. Exit 0 returns `True`,
   and exit 1 returns `False`.

Any other exit from either raises `git_mirror.GitError` naming the command.
`main`'s handler turns that into exit 2, as it does when
`export_saffron_dir` meets a broken mirror earlier in `_resolve_queue`.
Measured 2026-09-22 on git 2.54 on the host and git 2.39.5 in
`saffron/cell-base:python`. The first command exits 1 for a missing commit
and 128 for a missing mirror, on both. Run each command as
`git -C <mirror>`, not with `cwd=<mirror>`. A missing directory as `cwd`
raises `FileNotFoundError` before git runs. `git_mirror._git` raises on
every nonzero exit, so it cannot read these exit codes. Unlike
`_retirement_markers_at`, which swallows `GitError` on purpose, this
callable and its callers let it propagate. Run it in the
mirror, never the operator's checkout. A merge made on GitHub is absent from
a checkout that has not pulled, and criterion 2's witness merges on the remote
only.

**Criterion 1's witness.** Write it in `tests/test_scheduler.py` with the
existing `_write_spec`, `_task_at`, `_repo` and `_sha` helpers. It loops over
`sorted(DONE_STATES | REQUEUE_STATES)` in one plain `def`, with a fresh
`Ledger` under `tmp_path` for each state. Do not parametrise it.

- Three parent and child pairs. Parent A has two rows. Create first, so it
  has the lower `task_id`, the row at a spec sha not on disk, whose push the
  callable accepts. Then create the row at its current sha with no push.
  `tasks_by_repo` orders by `task_id` (`saffron/ledger.py:724`), so an
  implementation reading only the newest row per spec misses the push.
  Parent B's row pushed a commit the callable rejects. Parent C's row
  recorded no push. Record a push with `ledger.record_push`.
- The callable records every sha it is asked about.
- Assert A's child is a candidate and not refused, for every state. Assert the
  callable was asked about no sha but the two recorded ones. An
  implementation that skips a parent already merged asks about fewer, and
  passes.
- Last, once per test, pass a callable that raises `git_mirror.GitError`
  and assert with `pytest.raises` that `build_queue` raises it. This kills
  a `build_queue` that catches the error and answers no.
- For every state outside `DEPENDENCY_WAITING_STATES` and `MERGED`, assert B's
  and C's children are refused. `tests/test_scheduler.py` does not import
  `DEPENDENCY_WAITING_STATES` at module scope, so import it inside the
  function.

**Criterion 2's witness.** Write it in `tests/test_cli.py` with
`_repo_with_spec`, `_seed_repo` and `_seed_task`. The fixture holds six
specs. `_repo_with_spec` always writes `SY-1.md` from `spec_text`
(`tests/test_cli.py:1296`), so `SY-1` is parent 1. The other five go in
`extra_specs`, each child naming its parent in `depends_on`. Every parent
has an `EXHAUSTED` task at its current sha, so no parent is a candidate.

- Parent 1: a commit on `saffron/<id>`, pushed. Clone the bare origin into a
  second directory, merge that branch there with `--no-ff`, and push the
  default branch. Leave the checkout's default branch where it was, and
  check the checkout out on its default branch before the first queue.
  `git clone --mirror` points the mirror's `HEAD` at the checkout's current
  branch (`saffron/repos/mirror.py:67`).
- Parent 2: a commit on its own branch, pushed and never merged.
- Parent 3: a pushed sha of forty `b`s, which no repository holds.
- One `EXHAUSTED` task per parent at its current spec sha, the way
  `test_queue_reconciles_before_it_scans_so_the_refusal_gate_sees_current_state`
  computes it, with its push recorded.
- Run `cli.main([... "queue" ...])`. Assert parent 1's child is under the
  candidate count and above `refusals:`. Assert the other two children are
  refused, each reason naming its parent and `EXHAUSTED`.

- Then drive the pinned path twice, calling `cli._resolve_queue` with
  `stamp_orphaned=False` and a `task.PinnedBase`. A mirror ref can sit on
  either side of a pinned base. PACKAGE's `fetch_default_branch`
  (`saffron/phases/package.py:666`) moves the default branch ahead of a
  night's `base_sha`. An attended `saffron queue` or `saffron cell` sharing
  the mirror runs `ensure_mirror`, which fetches every ref from the checkout
  (`saffron/repos/mirror.py:63`) and can move it behind. `saffron batch`
  itself runs `ensure_mirror` once, in `check_readiness`
  (`saffron/preflight.py:472`), before it pins
  (`saffron/preflight.py:483`), and its rescan runs neither
  (`saffron/cli.py:810-813`).
- Ahead. Assert the mirror's default branch, `HEAD` and `FETCH_HEAD` all
  resolve to the merge commit. Pin `base_sha` to the checkout's default
  branch head from before the merge. Assert there is no candidate and
  parent 1's child is refused, its reason naming `SY-1` and `EXHAUSTED`.
- Behind. Move the mirror's `refs/heads/<default>` back to the checkout's
  default branch with `git update-ref`. Pin `base_sha` to the merge commit.
  Assert parent 1's child is the one candidate and the other two children
  are the refusals.

- Last, call the callable directly with a mirror path that does not exist
  and parent 1's pushed sha. Assert it raises `GitError`. Then call it with
  the real mirror and forty `b`s, and assert it returns `False`.

The fixture's origin is a local path, so no slug resolves and no `gh` runs.
The tasks carry no `pr_url`, so `reconcile` asks nothing.

**Wrong implementations, run against a prototype of this change.** Each line
names the witness that failed.

- Crediting any row with a push, without asking the callable: criterion 1.
- Asking the callable with an empty string for a row with no push: criterion 1.
- Crediting only `EXHAUSTED` rows, or only the two dead states: criterion 1.
- Reading only the newest row per spec: criterion 1.
- Leaving the callable unwired in `_resolve_queue`: criterion 2.
- Treating every exit code but 1 as landed: criterion 2, on the prototype
  that had no `rev-parse` step. With that step first, `merge-base` sees only
  commits the mirror holds, so this now passes the witness. A corrupt
  mirror is the only exposure left.
- Treating every nonzero exit as not landed, or catching `GitError` in
  `build_queue`: criteria 1 and 2's raising cases. Reasoned, not run, since
  the prototype predates them.
- Checking only that the mirror holds the commit: criterion 2.
- Running the check in the operator's checkout: criterion 2, because the
  merge is on the remote only.
- Testing ancestry against the mirror's `HEAD`, its `FETCH_HEAD` or its
  default branch ref instead of `base_sha`: criterion 2's ahead pass.
- Accepting a commit on either the pin or the mirror's `HEAD`: criterion 2's
  ahead pass.

**Every test you add must fail with this diff's source reverted.** Each
witness fails at base by an assertion or a `TypeError`. Neither fails to
collect. Criterion 1's passes the new keyword, and criterion 2's child is
refused. Import nothing new at module scope.

**Size.** A `bug` gets 300 changed lines. The prototype of both criteria and
their witnesses ran to 200 changed lines after `ruff format`. Allow about 230
with the docstrings.

**Commit as each witness passes**, before the full suite runs.
