---
id: 12
title: '`census` trusts the gate runner, and the gate runner is in the cell'
status: done
tier: null
closed: 2026-08-23
specs: []
prs: []
commits: [2a3e992, 3d27c4f]
cites: [§5.4]
related: [11]
---

## Problem

Promised by the split's spec (part 2.3) and not written until the fix wave.
`census`'s subtraction is exact about the two lists it is handed, and both lists
are produced inside the untrusted cell — by `/work/.saffron/gates/tests.py` and a
second pytest process. CLAUDE.md's founding line is that every control that
matters lives outside the cell; this one does not. Two routes, both measured:

- **A `conftest.py` that lies to `--collect-only`.** A
  `pytest_collection_modifyitems` that drops a test only when
  `config.option.collectonly` is false makes enumeration report a name the run
  never executes. `census` passes because the name is still collected; `tests`
  passes because the test never ran. The removal is invisible to both.
- **Uncommitted edits are invisible to every diff-reading gate and fully
  effective on every gate result.** `worktree.export_patch` and
  `worktree.changed_files` both diff `base_sha..HEAD`, while `CellExecutor` execs
  gates against `/work` — the worktree. So **any** uncommitted change is absent
  from `scope`, from `integrity` and from the packaged patch, while being live
  for the suite. The spec names `/work/.saffron/gates/tests.py`, and the
  `.saffron/**` `gate_config` pattern closes only the committed case — but the
  hole is wider than one file: an uncommitted edit to any source file changes
  what the suite is measuring, and the reviewer reads a patch that does not
  contain it.

Neither route argues for the diff-shaped removal check this branch rejected: that
one was evadable by a single adjacent added line and needed no `conftest.py` at
all. The honest statement of what shipped is that **`census` buys exactness
against an honest suite, not integrity against a hostile one.**

## Done looks like

a decision on the gate-runner trust boundary, which §5.4's
`no-network` gate and the gate contract both currently assume is cooperative. The
two candidate halves are independent: (a) gates run from a host-supplied copy of
`.saffron/gates/` rather than the one in `/work`, so an in-cell edit — committed
or not — cannot reach the runner; (b) the host refuses a dirty worktree at gate
time, or diffs `base_sha..worktree` so that an uncommitted edit is at least
*visible* to `scope` and `integrity`. Neither is v0.5's to build, and this item
exists so the choice is made deliberately rather than inherited.

## Record

**Status:** **done**, 2026-08-23 — both halves. The full account is in this
item's own body below, which was written as the fix landed; this line exists so
a scan of the file's status markers sees it.

**Done, 2026-08-23.** Both halves, which this item leaves as alternatives.
`.saffron/gates/` is exported from the mirror at `base_sha` and mounted read-only
at `/gates`, and the runner execs from there; a new core gate, `committed`, fails
the attempt when `git status` is not clean at gate time, one failure per path.
`DESIGN.md` rev 16 states the invariant both serve — anything that changes what
the suite measures must appear in the patch a human reads — and restates the
residual unchanged: a committed `conftest.py` still defeats `census`, and
`**/conftest.py` in this repo's `gate_config` routes that edit to a person rather
than failing it.

Two things this item does not contain, both worth more than the routes it names:

**Pinning the gates closes a baseline drift nothing had recorded, and that is the
stronger reason for doing it.** The baseline suite runs in the same cell and the
same worktree as head, before the agent starts, so the baseline ran the base
tree's gates and head ran whatever gates were in `/work` by then — a task editing
its own `tests` gate changed what the two subtracted sides mean. Suite drift by
construction, the same shape item 11 flags for `reverify`'s missing `thread_env`.

**`reverify` was a second copy of the same seam.** Its own cell, its own
`prepare_worktree`, its own `gate_executables(WORKTREE_MOUNT)`. Changing only
`session.py` would have left the two suites `reverify` subtracts coming from
different executables, and a required `gates_dir` would have broken PACKAGE at
runtime — invisible to `make check`, because the tests covering that path are
cell-marked and excluded by default. Found by review, not by running.

The dirty-tree half needed no new control flow: `committed` is a gate, so a dirty
tree gets the repair turn the loop already gives every `fail`, and a second
identical look ends the attempt on the no-progress rule.
