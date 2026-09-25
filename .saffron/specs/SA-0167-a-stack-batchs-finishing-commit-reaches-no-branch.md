---
id: SA-0167
title: A stack batch's finishing commit reaches no branch, because no gate suite judges it and nothing pushes it
type: feature
priority: 1
depends_on: [SA-0174]
touches:
  - saffron/finish.py
  - saffron/cli.py
  - tests/test_finish.py
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
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/report/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_suite.py
  - tests/test_package.py
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_task.py
budget_usd: 23
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      `finish.publish_finish(ledger, batch_id, sha, *, mirror, url, verify,
      gh, workdir)` pushes a green finishing commit and returns its lines.
      It calls `verify(sha, <the top layer's pushed_sha>)` once, while a
      branch in the mirror named `saffron-finish` and the batch id points at
      `sha`. It deletes that branch after `verify` returns or raises. It
      reads each layer's pull request base with `gh pr view`, bottom to
      top. With no escalation, it pushes `sha` to the top layer's branch at
      `url`, leased on that layer's `pushed_sha`. It records that push on
      the top layer's task and no other, before it removes its worktree. So
      a raise from that removal still leaves the push recorded. It returns
      one line, `finish.PUSHED` then `<sha12> to <branch>`, where `PUSHED`
      is `pushed `. The mirror's refs end as they began. The witness drives
      three layers and one layer, on a remote whose default branch is not
      `main`. It drives three layers whose worktree removal raises after
      the push.
    witness: tests/test_finish.py::test_a_green_finish_pushes_to_the_top_layer_and_records_the_push
  - claim: >-
      `publish_finish` pushes nothing in each of five cases, and returns one
      line starting `finish.ESCALATE`, `escalate: `. The remote's refs, the
      mirror's refs and worktrees, and each layer's `pushed_sha` stay as
      they were. The cases are checked in this order, all before the push.
      The suite reports new failures, or `verify` raises `PackageError` or
      `CellRuntimeError`, which both read as errored. A predecessor's
      branch head on the remote differs from the `predecessor_head` its
      layer recorded. A pull request's base reads back as other than its
      predecessor's branch, or the default branch for the bottom layer, or
      cannot be read. Last, the lease refuses the push because the top
      layer's branch moved. The witness drives each on three layers. It
      drives a red suite, and a suite that raises each of the two errors. It
      drives a hand push to the bottom and to the middle branch, and a wrong
      base on the bottom and on the middle. It drives an unreadable base on
      the top, and a hand push to the top.
    witness: tests/test_finish.py::test_each_escalation_leaves_the_stack_unpushed
  - claim: >-
      `finish.finish_suite(policy)` returns the spec and the policy that the
      finishing tree's gate suite runs under. The spec is a `chore` whose
      `touches` is `finish.FINISH_TOUCHES`, `.saffron/specs/*.md` and
      `.saffron/specs/done/*.md`, with no `forbidden` and no acceptance. The
      policy is `policy` with an empty `protected` list and an empty
      `integrity.suppressions`, and every other field as it was. Given this
      repository's own policy, a `GateSuite` under the two, against an
      empty baseline, finds no new failure in a diff that edits a spec and
      adds one in `done/`. The edit adds a line holding one of that
      policy's suppression tokens. Each of five paths added to that diff
      brings new failures on that path alone, one of them `scope`'s
      `out-of-scope`. The paths are `.saffron/policy.yaml`,
      `.saffron/specs/sub/x.md`, `.saffron/specs/x.txt`, `CLAUDE.md` and
      `docs/adr/0008-x.md`.
    witness: tests/test_finish.py::test_the_finishing_suite_passes_the_spec_directory_and_fails_every_other_path
  - claim: >-
      `saffron batch --stack` publishes the finish. When `commit_finish`
      returns a sha, `cli._stack_finish` prints `finish: committed <sha>`. It
      then calls `finish.publish_finish` and prints each line it returns
      after `finish: `. It passes the pinned mirror and url, a `workdir` of
      `out_dir / "finish" / <batch id> / "push"`, a `verify`, and
      `_guarded_gh` as `gh`. `verify(sha, base)` exports `.saffron/` from
      the pinned mirror at the pinned `base_sha` into `out_dir / "finish" /
      <batch id> / "gates"`. It calls `package_phase.reverify` on `sha` over
      `base`, with that export, the spec and policy `finish_suite` makes of
      its policy, and `repo_image.cell_tag(repo)`. It returns the count of
      new failures. The `gh` returns exit 127 when `run_gh` cannot start the
      program. A raise from `publish_finish` prints one line naming its type
      and message, and the exit code stays the stop reason's. A `None`
      commit calls no publish. The witness drives a sha, a raise and a
      `None` commit.
    witness: tests/test_cli.py::test_a_stack_batch_publishes_its_finish_through_the_finishing_suite
  - claim: >-
      `saffron batch` without `--stack` still hands `run_batch` its budget
      and its defaults.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
    preserves: true
  - claim: >-
      `reverify` still runs the whole gate suite, not the declared gates
      alone.
    witness: tests/test_package.py::test_reverify_runs_the_whole_gate_suite_not_the_declared_gates_alone
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 8 of its Done. It cites `DESIGN.md` §4.2,
§4.2.1, §5.4 and §5.7. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that the host commits the batch's revised and follow-up specs into
the top layer, and that nothing merges. Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, under "The
finishing layer" and "Linking", is the design.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. The next task is cut from
the last layer, its **predecessor**, and its pull request targets that
layer's branch.

**Step 8 is four specs.** `SA-0151` builds the finishing commit, and runs
it in `run_stack_batch`'s `finish` callable. It pushes nothing, and prints
`finish: committed <sha>, not pushed`. `SA-0174` writes `findings.json`
before the commit. This spec judges that commit with the repo's gate suite
in a gate-only cell. Then it compares each predecessor's head, reads every
base back, and pushes. `SA-0170` follows it, and links the pushed stack
with `gh stack link`. With `--ready` it marks each layer ready.

**What the tree base holds.** This spec's tree base is `SA-0174`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:133-136`). None of the chain
from `SA-0142` on exists at `68892367`, where every line number below was
read. So chain names are cited by symbol.

- From `SA-0145`: the `stack_layers` table, with `task_key`, `batch_key`,
  `position`, `spec_id`, `predecessor_key`, `predecessor_head` and
  `generation`, and `Ledger.record_stack_layer(task_id, *, position,
  predecessor_task_id, generation)`. It records the predecessor's
  `pushed_sha` as `predecessor_head`. The bottom layer's `predecessor_key`
  and `predecessor_head` are `NULL`.
- From `SA-0151`: `Ledger.stack_layers(batch_id)`, the batch's rows by
  `position`, each joined to its task for `task_id`, `pr_url`, `branch` and
  `pushed_sha`. `run_stack_batch` calls `finish(batch_id, unrun)` once,
  after the follow-ups, whatever the stop reason. `batch_id` is an `int`,
  and `unrun` holds the task id of each follow-up never reviewed.
  `finish.commit_finish(ledger, batch_id, unrun, *, mirror, workdir)`
  returns the commit's sha or `None`. The commit's parent is the top
  layer's `pushed_sha`, and it moves no ref. `cli._stack_finish` calls it
  with a `workdir` of `out_dir / "finish" / <batch id> / "tree"`. It prints
  `finish: committed <sha>, not pushed`, or one of two lines for `None`. It
  catches a raise and prints it, so the stop reason stands.
- From `SA-0174`: `finish.write_findings`, and a `pooled` keyword on
  `_stack_finish`. `_stack_finish` writes the findings before the commit.
- From `SA-0144`: `saffron batch --stack`.

**What the base already offers.** `reverify` runs the whole gate suite on a
commit and on a fresh baseline (`saffron/phases/package.py:466-575`). Each
runs in its own gate-only cell. It raises `PackageError` when a gate
errors or the two suites drift (`:558-574`), and returns the comparison.
Each gate-only cell seeds its tree by `git fetch` from the mirror, then
checks the sha out (`saffron/cell/worktree.py:89-95`). That fetch takes
`refs/heads/*` alone, so a commit no branch reaches cannot be checked out.
PACKAGE names that failure (`saffron/phases/package.py:722-726`). A failed
seed raises `CellRuntimeError` (`saffron/cell/worktree.py:105-108`,
`saffron/cell/runtime.py:35`), which is not a `PackageError`.
`push_with_lease` pushes a worktree's `HEAD` leased on an expected head, and
raises `LeaseRejected` when the branch moved (`:372-391`, `:76-77`).
`remote_sha` reads a branch's head on the remote, `""` when it is absent
(`:360-369`). `default_branch` reads the remote's `HEAD` (`:123-131`).
`add_worktree` and `remove_worktree` check a detached tree out of the
mirror and remove it (`saffron/repos/mirror.py:113-124`).
`Ledger.record_push` records a task's pushed head
(`saffron/ledger.py:1073-1079`). `repo_image.cell_tag` names a repo's cell
image (`saffron/repos/image.py:24-30`). `_guarded_gh` wraps `run_gh`, and
turns a `gh` that cannot start into exit 127 (`saffron/cli.py:1065-1079`).
`gh pr view <url>` names its repository by the URL. An unmarked test that
starts `gh` raises (`tests/conftest.py:13`, `:86-91`).

## Problem

Build four things.

1. **The finishing suite's terms.** In `saffron/finish.py`, add
   `FINISH_TOUCHES` and `finish_suite(policy)`, as criterion 3 states.
   Build the spec as an `intake.Spec` with the id `FINISH-0` and the title
   `the finishing layer`, since `reverify` takes a `Spec`. Build the policy
   with `model_copy`, so every field it does not name stays as the repo
   declared it.
2. **The publish.** In `saffron/finish.py`, add `ESCALATE = "escalate: "`,
   `PUSHED = "pushed "` and `publish_finish`, as criteria 1 and 2 state.
   Start every escalation line with `ESCALATE`, and the pushed line with
   `PUSHED`. `SA-0170` links only after a line that starts with `PUSHED`. Read the layers with `ledger.stack_layers`. The top is the last,
   and a layer's predecessor is the row whose `task_key` is its
   `predecessor_key`. In order:
   1. Point `refs/heads/saffron-finish/<batch_id>` in the mirror at `sha`
      with `git_mirror._git(mirror, "update-ref", <ref>, sha)`. Call
      `verify`, and delete the ref in a `finally` with
      `git_mirror._git(mirror, "update-ref", "-d", <ref>)`. A `PackageError` or a
      `CellRuntimeError` returns the errored line, and a count above 0
      returns the red line.
   2. Read the default branch with `package_phase.default_branch(url,
      cwd=mirror)`. For each layer with a predecessor, bottom to top, read
      the predecessor's branch with `package_phase.remote_sha`. A head
      other than the layer's `predecessor_head` returns the moved line.
   3. For each layer, bottom to top, run `gh pr view <pr_url> --json
      baseRefName --jq .baseRefName`. A non-zero exit reads as no base. A
      base other than the predecessor's branch, or the default branch for
      the bottom, returns the wrong-base line.
   4. Check `sha` out into `workdir` with `git_mirror.add_worktree`, and
      push it with `package_phase.push_with_lease` to the top's branch,
      expecting the top's `pushed_sha`. Straight after the push returns,
      inside the same `try`, call `ledger.record_push` for the top's
      `task_id`. Remove the worktree in the `finally`. `LeaseRejected`
      returns the top-moved line. Then return the pushed line.

   Write each line in full, naming what escalated and the heads or bases
   involved. The witnesses match each escalation on the words fixed in its
   notes below.
3. **The suite callable.** In `saffron/cli.py`, add
   `_finish_verify(*, pinned, repo, gates_dir)`, as criterion 4 states.
   `gates_dir` is `out_dir / "finish" / <batch id> / "gates"`, and the
   export goes there. Import
   `repo_image` as `saffron/task.py` does (`:45`).
4. **The wiring.** `_stack_finish` gains a `repo` keyword. Build it with
   the `repo` `_batch` resolves (`saffron/cli.py:783`). After a commit, it
   prints `finish: committed <sha>` in place of `SA-0151`'s line. A `None`
   commit keeps `SA-0151`'s lines and publishes nothing. It calls
   `finish.publish_finish` inside its own `try`, with `gh=_guarded_gh([])`,
   and prints each returned line after `finish: `. Reach
   `finish.publish_finish`, `package_phase.reverify` and
   `git_mirror.export_saffron_dir` through their modules at call time,
   since the witness replaces them there.

**Why every check runs before the push.** The design pushes no host commit
before the repo's gate suite reads it (items 40 and 97). The head and base
comparisons read the remote and write nothing. So a stack that escalates
stays exactly as its cells left it, and the operator starts from a known
state. A lease still guards the one push, since the top's branch can move
between the reads and the write.

**Why the commit gets a ref for the suite.** `commit_finish` moves no ref,
and each gate-only cell fetches `refs/heads/*` alone. So `reverify` could
not check the commit out, and its seed would raise `CellRuntimeError`. A
ref under `saffron-finish/` names the commit for the suite's span and no
longer. It sits outside `saffron/`, so no task's branch can collide with
it.

**How `scope` treats the host's commit.** `DESIGN.md` §5.4 states the rule.
`scope` passes a diff whose changed files are inside `touches` and match
neither `forbidden` nor `protected`. The repo's `protected` list holds
`.saffron/**` (`.saffron/policy.yaml:60-67`), and `scope_gate` fails every
changed file that matches it (`saffron/gates/core/scope.py:99-103`). So
under the repo's own list, every finishing commit is red. ADR 7 names the
host's commit to `.saffron/specs/` as the protected path's one exception.
Principle 29 asks each exception to carry its bound. The bound here is
`FINISH_TOUCHES`. The finishing suite runs `scope` with those `touches` and
an empty `protected` list. So a change inside the spec directory's
Markdown passes, and a change anywhere else fails `out-of-scope`. Every
protected path outside the spec directory still fails, under that code
rather than `protected`. `touches` also exempts these files from
`integrity`'s gate-config rule (`saffron/gates/core/integrity.py:226`,
`:259-270`), which lists `.saffron/**` (`.saffron/policy.yaml:121-127`).

**Why the suppression scan is off there too.** `integrity`'s suppression
scan reads every added line of every file
(`saffron/gates/core/integrity.py:272-285`). The cell's diff passes
`--no-renames` (`saffron/cell/worktree.py:132-144`). So a spec retired to
`done/` is a deletion and an addition, and each of its lines reads as
added. Of the 120 specs in `.saffron/specs/done/`, 20 quote a suppression
token, measured with `grep` on 2026-09-24. Under the repo's list, a queued
spec like them turns red the finish that retires it. `scope` already
confines the commit to Markdown, and a token in Markdown suppresses
nothing that runs.

**The bound's residual, under principle 29.** `FINISH_TOUCHES` still lets
a model-written spec text change its own frontmatter. A follow-up or a
revision can declare `pending_symbols`, and the `dead` gate then defers
those names once the stack merges. No gate reads that. The operator reads
the finishing layer's diff before the merge, and that read is the bound.
The delegate files a backlog item for it.

**What still turns the finish red, rightly.** A revised or follow-up text
that gains `prose` hits fails `prose`. A repo whose `elevate_on` reaches
the spec directory makes `size` block on the finishing diff. Both are the
repo's gates doing their job.

## Out of scope

- **Linking and marking ready.** `gh stack link`, `--ready` and `gh pr
  ready` are `SA-0170`'s. Until it lands, a pushed stack stays unlinked and
  every pull request a draft.
- **The escalation as a record fact.** No spec owns the fact kind yet. So
  an escalation is a printed line, `finish: escalate: ...`, and nothing
  more.
- **This repo's queue smoke test, and `census`.**
  `tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue`
  copies the live `.saffron/specs/` and pins its queue
  (`tests/test_scheduler.py:2451`, `:2462-2487`). A finishing commit retires
  specs, so the pinned lists no longer hold, and `tests` fails. Two tests in
  `tests/test_queued_specs.py` take one case per queued spec file
  (`:66-67`, `:102-103`). A retired spec removes its cases, and `census`
  fails on any removed name (`saffron/gates/core/census.py`). So in this
  repo, each finish with a layer escalates red. The finish reads it as the
  red suite it is. Both tests are this repo's design, and core knows
  nothing of them. The delegate files one backlog item for both.
- **A prune while the temporary ref lives.** `ensure_mirror` fetches
  `--prune` with `+refs/*:refs/*` (`saffron/repos/mirror.py:60-63`). A
  concurrent call in that window deletes the temporary ref and any layer
  branch the remote lacks, and the suite's seed fails. That reads as
  errored, and nothing is pushed.
- **A failed delete of the temporary ref.** A raise from the `finally`'s
  `update-ref -d` leaves the ref in the mirror and reaches
  `_stack_finish`'s catch. The next finish of the same batch id
  overwrites it.
- **A lower branch moved after the comparison.** The heads are read before
  the push, and the lease guards the top branch alone. A hand push to a
  lower branch between the read and the push goes unseen.
- **A hand push before the handoff's fetch.** `SA-0145` records the
  predecessor's `pushed_sha`, and the handoff cuts from the head it fetched.
  A hand push between the two makes them differ, so it escalates too.
- **`DESIGN.md` §5.4's `scope` row.** It does not name the finishing
  suite's exception. ADR 7 carries it, and `DESIGN.md` is protected.
- **Merging.** Nothing merges.
- **The vocabulary.** `CONTEXT.md` has no entry for the finishing layer or
  an escalation. Backlog item b-466005 files them by hand.

## Notes for the agent

**Every criterion but the last two is new code.** No text at the tree base
publishes a finish. So criteria 1 to 4 declare a witness and no mutant, and
`witness` reports `skip` for them. Import `publish_finish`, `finish_suite`,
`ESCALATE` and `FINISH_TOUCHES` inside each test body, so the reverted run
fails rather than failing to collect. Criteria 5 and 6 name tests that pass
now.

**The tree base's command-line witnesses change.**
`test_a_stack_batch_commits_its_finish_and_survives_a_raise` (`SA-0151`)
asserts `finish: committed <sha>, not pushed`, and its mirror is a dummy
path. Make it assert `finish: committed <sha>`. Other tests at the tree
base drive `_stack_finish` to a sha too, such as `SA-0174`'s. In each,
replace `finish.publish_finish` with a recorder that returns an empty list.

**Criteria 1 and 2 share one arrangement** in `tests/test_finish.py`. Use
the isolated git environment and helpers `SA-0151`'s tests already hold.
Write it as a helper, `_stack(root, count)`, since `SA-0170`'s witness
builds on it. It builds a fresh stack for each case under its own
directory:

- A work repository on `trunk` commits `a.py`. It then branches
  `saffron/TE-1` to `saffron/TE-<count>`, each one commit on the last.
- It checks `trunk` out again, clones itself `--bare` as the remote, and
  the remote is cloned `--mirror`. The remote's `HEAD` must name `trunk`.
  Measured: a clone taken with a layer checked out names that layer, and
  the bottom's base then reads wrong.
- On a `Ledger` in the directory, one batch holds a task for each layer,
  created top first. Each is packaged `READY_FOR_REVIEW` at its head, with
  its pull request `https://github.com/o/r/pull/<100 + n>`. Then each layer
  is recorded, top first, at position `n` on the one below. So neither the
  task ids nor the order recorded follow position.
- The finishing commit is `git commit-tree` of the top head's tree, with
  the top head as its parent.
- `url` is the bare remote's path.

Beside it, `gh` is a fake that records each argv. It answers `pr view`
with the layer's right base, unless a case overrides it, and exits 0 on
any other call. `verify` records each call. While it runs, it asserts that
`refs/heads/saffron-finish/<batch id>` in the mirror resolves to its first
argument. Keep `git for-each-ref` of the remote and of the mirror before
each call.

**Criterion 1's witness** runs three layers, then one layer, and asserts
in each:

- the calls to `verify` are exactly `[(sha, top head)]`
- the remote's refs are as before, save the top branch, now at `sha`
- the `pushed_sha` of the layers are their heads, save the top's, now `sha`
- `gh`'s calls are exactly each `pr view` bottom to top
- the lines are exactly `[f"pushed {sha[:12]} to <top branch>"]`, and the
  line starts with `PUSHED`
- the mirror's refs are as before, and one worktree is listed there

Last, on three layers, it replaces `git_mirror.remove_worktree` with one
that removes the tree and then raises `OSError` for the push's worktree.
It asserts the raise, and the top layer's `pushed_sha` now `sha`. These
fail it:

- the layers taken by task id, or in the order recorded
- no ref naming the commit while the suite runs
- the ref left behind after the suite
- the suite based on the bottom layer's head
- the push to the bottom layer's branch
- no push recorded, or the push recorded on the bottom layer
- a raise from `remove_worktree` after the push skips the record
- the default branch spelled `main`
- the bottom layer's base left unchecked
- the worktree left registered

**Criterion 2's witness** runs nine cases on three layers. It asserts one
line, its start, the remote's and the mirror's refs unchanged, the
`pushed_sha` of the layers unchanged, and one worktree listed. It asserts
`gh`'s calls are exactly the `pr view` calls given, bottom to top.

| case | arrangement | line starts | `pr view` calls |
|---|---|---|---|
| red | `verify` returns 2 | `escalate: red suite, 2 new failure` | 0 |
| errored | `verify` raises `PackageError` | `escalate: the finishing suite errored` | 0 |
| cell broke | `verify` raises `CellRuntimeError` | `escalate: the finishing suite errored` | 0 |
| bottom moved | a hand push to `saffron/TE-1` on the remote | `escalate: saffron/TE-1 is at` | 0 |
| middle moved | a hand push to `saffron/TE-2` | `escalate: saffron/TE-2 is at` | 0 |
| bottom base | `TE-1`'s base reads `saffron/TE-9` | `escalate: TE-1's pull request targets saffron/TE-9, not trunk` | 1 |
| middle base | `TE-2`'s base reads `trunk` | `escalate: TE-2's pull request targets trunk, not saffron/TE-1` | 2 |
| top unread | `TE-3`'s `pr view` exits 1 | `escalate: TE-3's pull request targets nothing readable, not saffron/TE-2` | 3 |
| top moved | a hand push to `saffron/TE-3` | `escalate: saffron/TE-3 moved since its push` | 3 |

A hand push clones the remote at that branch, commits a file, and pushes
it back. It also asserts each line starts with `ESCALATE`. These fail it:

- the suite's count ignored, or an errored suite read as 0
- a `CellRuntimeError` from the suite left to escape, or read as red
- the push before the suite, or before the base read-back
- the heads compared for the top layer alone, or for the first layer with
  a predecessor alone
- a predecessor's head read from the ledger, not the remote
- a push leased on the branch's current head, which is no lease
- the bottom layer's base left unchecked

**Criterion 3's witness** loads this repository's policy with `load_policy`
and asserts its `protected` and `integrity.suppressions` are not empty. It
asserts the returned policy's `model_dump()` equals the original's with
those two emptied. It asserts the spec's `type` is `chore`, its `touches`
equals `list(FINISH_TOUCHES)`, and its `forbidden` and `acceptance` are
empty. It builds `GateSuite(gates={}, spec=spec, policy=policy,
diff_base="base")` and compares a head `_Tree` against an empty
`_Tree`'s baseline. `_Tree` is the in-memory tree in `tests/test_suite.py`
(`:19-60`). Import it, and leave that file as it is. Write each file of the
diff by hand, in the `a/` `b/` shape `scope` reads, with one hunk of added
lines. Take the suppression token from the loaded policy's
`integrity.suppressions`, and never spell one in the test file, since the
repo's own `integrity` scans it. These fail it:

- the protected list kept, or the suppression scan kept
- `touches` of `.saffron/**`, `.saffron/specs/**` or
  `.saffron/specs/**/*.md`
- no `touches`, which makes `scope` skip
- a fresh `Policy`, which drops the repo's declared gates

**How the list was measured.** A throwaway run on 2026-09-24 at
`68892367` stood in for `SA-0145`'s `stack_layers` table and
`record_stack_layer`, and for `SA-0151`'s `Ledger.stack_layers`. It loaded a
prototype of `finish_suite` and `publish_finish`, and ran prototypes of
criteria 1 to 3's witnesses on the host's git. The right build passed all
three. Each of the 29 wrong builds above was applied as a text edit to the
prototype, and each failed its witness. The push before the suite and
before the read-back were modelled by moving the push block.

**Criterion 4's witness** follows `SA-0151`'s witness for `saffron batch
--stack`, with `_readiness_passes` (`tests/test_cli.py:2603-2621`) and
`_fake_batch_resolution` (`:2624-2640`). The pinned mirror is
`/tmp/pinned-mirror.git`, the url `https://github.com/o/r.git`, and
`base_sha` is `a`×40. The fake `run_stack_batch` calls `finish(3, [5, 6])`,
a batch id and its `unrun`, and returns `UNTIL`. It replaces
`finish.write_findings` with a stub that takes `*args, **kwargs` and
returns a path. It replaces `finish.commit_finish` with one that takes
`*args, **kwargs` and returns `c`×40. It replaces
`git_mirror.export_saffron_dir` with a recorder that writes this
repository's `.saffron/policy.yaml` under `dest / ".saffron"` and returns
`dest`. It replaces `package_phase.reverify` with a recorder whose result
has two `new_failures`. The fake `publish_finish` records its arguments,
calls `verify("c"×40, "d"×40)` and keeps its result, and returns one line.

The first run asserts exit 0, the commit line, and the returned line after
`finish: `. It asserts each argument, `verify`'s 2, and one export of the
pinned mirror at `a`×40 into `<out>/finish/3/gates`. It asserts
`reverify`'s arguments: the mirror, `c`×40 over `d`×40, that directory,
and `saffron/cell:<repo name>`. Its policy has an empty `protected` list
and the repo's gates, and its spec's `touches` is `FINISH_TOUCHES`. Then,
under `monkeypatch.context()`, it makes `cli.run_gh` raise `OSError`, and
the kept `gh` returns exit 127. Two more runs follow, each with its own
`--home`. A `publish_finish` raising `GitError("gone")` prints `finish:
nothing published: GitError: gone` and exits 0. A `None` commit calls no
publish. These fail it:

- a `gh` that raises on a program it cannot start
- the repo's policy passed to `reverify` unchanged
- the gates exported at another commit, or read from the operator's
  repository
- `verify` returning the comparison, or whether it is red, not the count
- `SA-0151`'s `not pushed` line kept
- a publish on a `None` commit
- a raise that reaches `main`, which exits 2

Criterion 4 is unmeasured. `saffron batch --stack` and `_stack_finish` do
not exist at `68892367`.

**What the witnesses leave undriven.** They drive no layer without a pull
request URL, and no `remote_sha` or push that raises `PackageError`. Nor do
they drive a `verify` raise other than the two criterion 2 names. Each
reaches `_stack_finish`'s catch, and nothing is pushed. Build each as the
Problem states.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path in `touches` is in `elevate_on`, so `size` is advisory
at the `feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`).
A prototype of the whole change, formatted with `ruff`, was measured with
`size_gate` at `68892367`. It came to 2048 tokens.

| part | lines | tokens |
|---|---|---|
| `finish_suite`, `ESCALATE`, `PUSHED` and `publish_finish` in `saffron/finish.py` | 109 | 406 |
| criteria 1 to 3's witnesses in `tests/test_finish.py` | 350 | 1122 |
| `_finish_verify` and the wiring in `saffron/cli.py` | 55 | 162 |
| criterion 4's witness in `tests/test_cli.py` | 113 | 358 |

The test prototype carried its own git helpers, which `SA-0151`'s tests
already hold. They measured 62 tokens, and they go. It carried no
docstrings, and it lacked the edits to the tree base's witnesses. About
130 more tokens cover those. So the estimate is about 2120 tokens, 71% of
the ceiling.
