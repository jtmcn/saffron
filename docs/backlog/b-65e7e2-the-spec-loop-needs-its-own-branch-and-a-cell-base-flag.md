---
id: b-65e7e2
title: The spec loop merges every spec edit to `main` before a cell can run it, because `saffron cell` has no `--base`
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.2.1, §5.7]
related: [157, 137, 33]
---

## Problem

The operator's proposal, 2026-09-18, from the spec loop's run 8.

`saffron cell` cuts its worktree from the default branch, or from a
`depends_on` parent's pushed branch (`_resolve_stacked_on`,
`saffron/task.py:117-164`). It takes no base of its own (`saffron/cli.py:88-95`).
A cell cut from `main` carries the spec text on `main`. A spec edited on
another branch reaches the cell only as a `spec_drift` preflight line, which
reports and does not refuse (`saffron/cell/session.py:1320-1321`).

So every spec edit the loop's step 1b makes has to merge to `main` before the
cell that runs it. Run 8 needed three spec pull requests merged mid-loop:
#350 (all five specs), #352 (`SA-0107` and `SA-0102`) and #361 (`SA-0108`).
Each was an operator merge that stopped the loop. A stacked child's branch
also carries its spec as of the parent's cut, so a reviewer reading the branch
saw the pre-edit spec (#360).

## Done looks like

The loop cuts its own branch at start. The spec edits are its bottom commit,
and every cell stacks on it:

- `saffron cell --base <branch>` cuts the worktree there and opens the PACKAGE
  pull request against it.
- The loop driver's `snapshot` and `next` read specs at the loop branch
  (item 157 is the same defect from the other side).
- The operator ratifies spec edits in the stack review. Step 1b's answers stay
  the approval before money is spent.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353), at the operator's request.
