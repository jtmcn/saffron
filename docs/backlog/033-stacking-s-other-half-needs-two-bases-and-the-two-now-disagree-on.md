---
id: 33
title: Stacking's other half needs two bases, and the two now disagree on purpose
status: done
tier: null
specs: [SA-0020, SA-0022, SA-0025, SA-0026]
prs: [81]
commits: [5ab674e, ab23523]
cites: [§3.1, §4.2, §4.2.1, §5.3.1, §5.7, §9]
related: [11, 13, 32]
---

## Problem

**Status:** **done** — all three specs merged: `SA-0022` (PR #81),
`SA-0025` (#82) and `SA-0026` (#84). `CellSpec.stacked_on` is distinct from
`base_sha`, PACKAGE resolves a real parent, and `CONTEXT.md` carries the **Tree
base** entry the split needed.

`SA-0020`'s first attempt (ledger task 20, `EXHAUSTED` at $14.43 against a $16
budget, 2026-08-30) found that a stacked task — one whose parent is still only
`READY_FOR_REVIEW`, item 32's remaining half — needs `worktree.prepare_worktree`
to check out the parent's own unmerged branch head, ahead of `base_sha`, while
the exported patch was still computed as `export_patch(container, base_sha)`
and so captured the parent's entire diff plus the child's own. It could not fix
that: `saffron/phases/**` was forbidden to it, and the `touches` insufficiency
only surfaced after the plan checkpoint, past §5.3.1's one door out.

This split the remaining work in two. This item is the half with no production
trigger: `CellSpec.stacked_on`, distinct from `base_sha`, and
`worktree.prepare_worktree`'s matching parameter, so a worktree can be built on
a base other than the run's pin and a patch can be exported against that same
base rather than against `base_sha` — proven with a real two-commit parent
branch and a real child commit on top, not a value a test constructs and then
reads back. `cli.py` sets `stacked_on=None` explicitly at the one place a
`CellSpec` is built, so `depends_on` is not consulted on that path at all and
no real task stacks yet. `SA-0025` resolves a real parent onto the field, wires
it into `_drive_cell`, teaches PACKAGE to target the parent's branch, and
widens the dependency gate to admit a `READY_FOR_REVIEW` parent.

**The disagreement this creates is real the moment `SA-0025` wires it up, and
it is worth deciding now rather than at the hour nobody is watching.** A
stacked worktree's tree is the parent's unmerged commits plus the child's own —
code the gate executables and the policy declaring them, both exported from
`base_sha` (item 13), have never seen. Two ways that can go wrong: a gate role
the parent's own commits added exists in the tree but not in the exported
`.saffron/gates/`, so `run_suite` never invokes it — a silent gap, not a
`skip` that names itself; and a gate that would judge the parent's own change
differently under the parent's own policy update instead judges it under the
policy that predates that update.

**Decision: `base_sha` wins — the gates and the policy declaring them stay
resolved from it, stacked task or not.** Two reasons, not one. First, this
spec's own out-of-scope line is explicit that it does not redefine what
`base_sha` means; moving the gate source to `stacked_on` for some tasks and not
others *is* that redefinition, one call site at a time, and item 13 already
spent a whole item settling gates-from-`base_sha` as the run's pin — a second,
task-local exception to it is a third thing to keep in step with the first two
rather than one settled fact. Second, `base_sha` is the one value every task in
a run shares; a gate source that moved with `stacked_on` would mean two
sibling tasks stacked on two different parents run under two different gate
suites inside the same run — a suite-drift vector already named once, for
`reverify`'s missing `thread_env` (item 11), and the common case here rather
than the exception.

**What this defers, by name, for `SA-0025` to inherit rather than rediscover.**
A parent that adds or changes a gate role stays invisible to a child stacked on
it until the parent lands on the default branch and `base_sha` itself moves
past it — the same shape item 13 already accepted for an operator's own
branch, now also true of a dependent task's parent. Closing that without
moving what `base_sha` pins means exporting a second, `stacked_on`-sourced gate
set for a stacked task alone and running both suites, which is unbuilt and is
not this item's to build: the requirement here was that the disagreement be
recorded, not resolved.

**`package.py`'s own read of the base, which looks correct and is not.**
`saffron/phases/package.py:526` is `json.loads(patch.json)["base_sha"]`, and it
feeds `assert_base_objects`, the `git apply --3way`, `needs_reverification`
and the pull request body's provenance. `SA-0022` records `tree_base` beside
`base_sha` precisely so that read *can* be made correct — for a stacked child
the patch is relative to `tree_base`, and applying it to `base_sha` puts
parent-relative hunks on a tree without the parent's commits: `MERGE_FAILED`
at best, an apply that looks right at worst. It is the likeliest place
`SA-0025` gets this wrong, because a one-word read that is correct today
raises no question. `SA-0025` also owes `CONTEXT.md` an entry for the second
base: `tree_base` is a new noun and it is already in a durable artifact.

**Re-verification is the second caller, and it is not covered above.**
`saffron/phases/package.py` calls `prepare_worktree` a second time, building
its baseline and head worktrees from the current default-branch head. For a
stacked child that is the wrong baseline outright — the parent's commits are
not in it — which is a different failure from the gate-source disagreement
this item decides. `saffron/phases/**` is forbidden to `SA-0022`, so recording
it here is the only action available; `SA-0025` owns the file and the fix.

**Decided and implemented, 2026-08-31 (`SA-0025`).** `package()` now takes an
optional `parent_branch`. Unset — every caller today — nothing above changes:
`target_branch`/`target_head` resolve to `default`/`fetch_head` exactly as
before, and reading `tree_base` instead of `base_sha` for the patch's preimage
check is a no-op, because `SA-0022` already writes the two equal for an
unstacked task. Set, and the parent's own commits are not yet an ancestor of
`fetch_head`, PACKAGE opens against the parent's current head instead —
fetched fresh, so a parent that merged, force-updated or was deleted between
the child's start and its push is caught (named as `ParentGone`, one message
for "gone", a different one for "moved to a commit the mirror cannot reach")
before a pull request opens against a branch that is not there. A parent
already merged into `fetch_head` falls back to the ordinary target rather than
re-fetching a branch that is routinely deleted the moment its own PR lands.

This also answers the re-verification baseline question left open above:
**the fresh baseline is whichever tree the child is ultimately packaged
against** — the parent's current head when stacked and the merged-fallback
has not fired, `fetch_head` otherwise — never `fetch_head` unconditionally.
`needs_reverification` and `reverify`'s `new_base_sha` both read that one
value (`target_head`) now, closing the gap the paragraph above named: a
stacked child's baseline used to omit the parent's own commits entirely. The
disagreement decided above — the gates and the policy declaring them staying
pinned to `fetch_head`'s export regardless of stacking — is unchanged; only
the baseline commit `reverify` diffs against moved.

**Left unrecognised, by design: a squash-merged parent.** The ancestor check
above is `git merge-base --is-ancestor tree_base fetch_head`, mirror-local.
GitHub's squash-merge writes a new commit object onto the default branch that
shares no history with the parent branch's own commits, so a squash-merged
parent whose branch was then deleted — the ordinary shape once a PR lands —
reads as "gone without merging" rather than "merged": `ParentGone` fires and
the task ends `MERGE_FAILED` for a change that, in fact, already shipped.
Recognising a squash merge needs GitHub's own merge record (the PR's `merged`
flag and `merge_commit_sha`), not anything the mirror holds, and building that
is not this item's to do. The failure mode this leaves is a false negative
that costs a task, never a pull request opened against a branch that is not
there and never a silent double-apply of the parent's hunks — the two shapes
this item exists to rule out.

**Two more shapes accepted rather than solved, and one debt reassigned.**

- *A parent force-pushed to a history that no longer contains `tree_base`.*
  Distinct from the two `ParentGone` names: the fetch succeeds and the head is
  reachable, so nothing above fires, and the child's patch three-way-rebases
  onto a divergent parent. In the bad cases that conflicts and ends
  `MERGE_FAILED`; in the benign-looking ones it can resurrect content the
  force-push removed. A `merge-base --is-ancestor tree_base parent_head` check
  would name it, and `SA-0026` — which is what first produces a real parent to
  force-push — cannot make it: `saffron/phases/**` is forbidden there. It needs
  a spec of its own, after stacking is live and the shape can be measured.
- *A pruned mirror inverts a gone parent's classification.*
  `assert_base_objects(mirror, tree_base)` has to precede the fetch — it is
  checking for objects the fetch would otherwise supply — so a parent deleted
  without merging, in a mirror since gc'd, raises `PackageError` and exits 2
  before the `ParentGone` path can make it this task's own `MERGE_FAILED`.
  Latent and gc-dependent; the ordering is right and the classification is not.
- *`CONTEXT.md` still owes `tree_base` an entry.* This item asked `SA-0025` for
  it, and `SA-0025` forbids itself `CONTEXT.md` — correctly, since its
  documentation half is by hand. `SA-0026` carries the sentences, and carries
  this one with them: `tree_base` is a noun in a durable artifact and the
  glossary does not have it.

**Decided and implemented, 2026-08-31 (`SA-0026`).** The producer is real now.
`cli._resolve_stacked_on` reads `Ledger.tasks_by_spec_id(repo_id,
depends_on[0])` — every task row this repo has ever run for that one parent
spec id, across every `spec_sha` it has carried, the same "merging is
permanent" reach `merged_anywhere` already takes, because this attended path
never reads the parent's spec file and so has no current sha to filter rows
to. Among those rows, the newest one still in `scheduler.
DEPENDENCY_WAITING_STATES` (`READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN`) is
"the parent's task" — the same waiting-outranks-dead precedence
`_dependency_refusal` already gave the gate's own refusal text. Not the same
row, though: the gate reads only the parent's current `spec_sha`, so a parent
whose spec text moved after its pull request opened has a waiting row here and
none there. The branch is real either way; the gate decides whether the
dependent runs, and the resolver only decides what it is cut from. Its `pushed_sha` becomes `CellSpec.stacked_on`, its `branch`
becomes `package()`'s `parent_branch`, and both are `None` together —
never one without the other — the moment either is missing, empty, or not a
resolved sha: a merged or retired parent (no waiting row at all) yields an
ordinary unstacked cell rather than a `CellSpec.__post_init__` `ValueError`.
K=1: only `depends_on[0]` is ever a stacking candidate. The dependency gate
(`scheduler._dependency_refusal`) now returns `None` — admits — for the three
waiting states instead of refusing them with the sentence this item's own
neighbours quoted; that sentence is gone, not left beside a gate that no
longer says it.

The two shapes named above are exactly as open as they were; shipping the
producer did not close either. Force-push detection is still unbuilt —
`saffron/phases/**` stays forbidden here, so the `merge-base --is-ancestor
tree_base parent_head` check the first bullet names is recorded again, not
added, now that a real stacked parent exists for one to force-push onto.
`CONTEXT.md`'s `tree_base` entry is still owed by hand — this spec forbids
itself that file too, for the same reason `SA-0025` did.

**A canary fired that this spec had no file to retire, and the deny list is
what made that a defect.** `SA-0025` planted `tests/test_package.py::
test_the_operators_reachable_packaging_path_is_unstacked`, asserting the
literal string `parent_branch` does not appear anywhere in `saffron/cli.py`
— true the day it was written, and false the moment a producer exists, by
the test's own docstring ("the one caller reaching `package()` in production
must not pass a parent"). `SA-0026` is that producer, and `tests/test_package.py`
is not among its `touches`, so the cell could satisfy the guard's letter or
fail the `scope` gate and nothing else. It spelled the keyword by
concatenation (`{"parent" + "_branch": ...}`), said so in a comment, and
recorded it here — the right handling of a box a spec put it in, and both
review lenses still flagged the result, correctly: a green guard that proves
only the absence of one spelling misleads whoever next reads it.

Retired by hand at review, 2026-08-31. The text search is deleted rather than
rewritten — it asserted a property of `cli.py` from `tests/test_package.py`,
and a source grep is satisfiable by any caller willing to spell the keyword
differently. Both halves are asserted on the call now, in `tests/test_cli.py`:
`test_a_stacked_worktree_passes_its_parents_branch_to_package` for a stacked
run, and `test_an_unstacked_worktree_passes_no_parent_branch_to_package` for
the converse. `cli.py` spells the keyword.

**The rule this is the second instance of.** A spec that turns on a
capability must own the tests that assert the capability is off, or its
`touches` hands the agent a choice between a false green and a `scope`
refusal. `SA-0022` missed `saffron/cli.py`; this one missed
`tests/test_package.py`. Both were caught in review rather than by the gate
that could have caught them — an inertness guard names the spec that will
retire it, and nothing checks that the named spec can reach the file. At
three instances the rule is wider than tests: `SA-0026` could reach neither
`saffron/cell/session.py`'s nor `saffron/phases/package.py`'s comments saying
stacking was off, both corrected by hand at review. **A spec that turns on a
capability must be able to reach every artifact that says the capability is
off** — the guard, the comment, and the design sentence alike.

**The ledger's recorded sha is not the branch, and nothing put the branch in
the mirror.** Found in review, not by a gate, and it would have killed the
first real stacked run. `_resolve_stacked_on` originally returned the parent
task's `pushed_sha`; two separate problems with that:

- *Nothing fetches it.* `ensure_mirror` fetches `+refs/*:refs/*` from the
  operator's **local checkout** with `--prune`, so a parent branch they do not
  happen to have checked out is deleted from the mirror; `fetch_default_branch`
  fetches only the default branch; and the cell's own seed (`worktree.py`)
  fetches the mirror's default refspec. Measured: this repository's mirror had
  already pruned `refs/heads/saffron/SA-0025` while that pull request was open,
  and its `refs/heads/saffron/*` set is exactly the operator's local branches.
  `git checkout -b <branch> <parent_sha>` in the seed is then
  `fatal: unable to read tree`, exit 2, naming neither the parent nor why.
  `fetch_default_branch`'s own comment made this argument one branch over.
- *It is a commit behind.* `pushed_sha` is written once, by PACKAGE. Every
  review fix an operator commits by hand moves the branch past it. Measured on
  this pull request: task 26's `pushed_sha` was `ab23523` while
  `saffron/SA-0026`'s head was `5ab674e` — a child would have been cut from a
  tree containing the concatenation dodge the review had already removed.

Both are one fix: the ledger says **which branch**, `fetch_parent_branch`
(`SA-0025`, one branch over from where it was already used) says **which
commit**. `ParentGone` there is an unstacked cell and a printed line, not a
failure — a deleted parent branch has either merged or been abandoned, and
neither is worth killing an attended run over.

**The overlap refusal shadowed the widened gate completely.** `_refuse` checks
a candidate's `touches` against every open pull request's changed files
*before* it reaches the dependency check. A parent at `READY_FOR_REVIEW` has an
open pull request by definition, and almost every spec here touches
`docs/BACKLOG.md` — so nearly every stacked child was refused on its own
parent's pull request and never reached the admission this item exists to
build. `SA-0025`'s pull request changed `docs/BACKLOG.md`, which is in
`SA-0026`'s `touches`: this very pair would have been refused. Fixed at review
by exempting `depends_on[0]`'s branch, and only that one — a child cut from
its parent's tree already contains the parent's changes, which is what
stacking is; any other task's pull request over the same file is still the
collision the check exists for.

**The by-hand half, done at review rather than owed.** `DESIGN.md` and
`CONTEXT.md` are `forbidden` to every spec in this sequence, deliberately, so
an operator corrects them: §4.2's dependency-gate rule and §4.2.1's `depends_on`
paragraph (which said every other parent state is still refused), §5.7 (which
described one base, and now carries the two-bases paragraph and the
fetch-never-remember rule), §9's v2 list (which still deferred stacking), and
`CONTEXT.md`'s new **Tree base** entry. §3.1's frontmatter example needed no
edit: `depends_on: [TE-0139] # satisfied at READY_FOR_REVIEW` was the design's
stated intent all along, and is true for the first time.
