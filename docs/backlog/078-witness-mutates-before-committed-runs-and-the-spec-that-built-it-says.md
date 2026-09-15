---
id: 78
title: '`witness` mutates before `committed` runs, and the spec that built it says the opposite'
status: done
tier: 1
specs: [SA-0062]
prs: [154]
commits: [290f070, 4b533d5]
cites: [§5.4, §5.4.1]
related: []
---

## Problem

**Status: done, 2026-09-12** — the `DESIGN.md` half by hand, as a paragraph in
§5.4.1 stating the ordering and the self-guard it obliges. Done in code
2026-09-07; what follows is the record of that half. The two fixes on
PR #154 itself (`4b533d5`, `290f070`): `worktree.source_mutated` yields a reason
when the mutant's file is dirty — the shape `revert` uses, landing `witness` on
`skip` — and a failed write restores from `HEAD` before it re-raises, so a
truncation cannot outlive the failure. What is left is the third paragraph of
"done looks like": the `run_suite`-before-`committed` ordering is load-bearing
and written down nowhere. One sentence in §5.4, by hand — a gate that mutates
the tree self-guards against dirtiness, because `committed` runs after it.

Found reviewing PR #154 (`SA-0062`), 2026-09-06. The spec justifies a
`git checkout HEAD` undo with *"the agent's work is committed by the time gates
run — `committed` is what guarantees it"*. Measured: it does not.
`cell/session.py:1008` calls `run_suite`, which holds `witness`;
`committed_gate` is not called until `cell/session.py:1049`. `witness` runs
first, on a tree that may still be dirty, and the host checkpoint is later
still.

So the undo restores to `HEAD` a file the agent may have edited and not
committed. The uncommitted work is destroyed, and `committed` — the one gate
whose job is to notice a dirty tree — then sees a clean one. This is the exact
failure the sibling gate refuses to cause: `gates/core/revert.py:180` skips when
its paths are dirty, because *"no evidence about theater is worth destroying the
agent's uncommitted work and blinding the gate that would have caught it."*
`worktree.source_mutated` performs the identical restore with no such check. The
inconsistency is visible inside the new code: `_read_file` documents that it
reads the working tree, *not* `HEAD`, and the undo then restores `HEAD`.

A second shape in the same function. The write is `> path`, which truncates
before `base64 -d` produces anything, so a non-zero exit raises out of
`__enter__` over a file that is now mutated or empty. `gates/core/witness.py:79`
states the contract that forbids this — *"a raise from `__enter__` must mean
nothing was changed"* — and names this precise case as the one a host mutator
cannot reach: *"a container exec that applies the edit and then loses the
connection is exactly the shape that is not."* It adds that all three
obligations *"bind every implementation"*. Flagged in advance, in a file the
spec was forbidden to edit, and not met.

Both are latent only until a spec declares a mutant, which `SA-0062`'s own
*Out of scope* says is the next one.

**Done looks like** `source_mutated` yielding a reason when the mutant's file is
dirty — the shape `revert` already uses, landing `witness` on `skip` — and a
failed write either restoring from `HEAD` before it re-raises or going through a
temp file inside the cell, so a truncation cannot outlive the failure. Then the
ordering itself: either `committed` moves ahead of `run_suite` in `_suite`, or
`DESIGN.md` records that a gate which mutates must self-guard against dirtiness.
Right now that ordering is load-bearing and written down nowhere, which is how a
spec came to assert its opposite and pass review.
