# The independent review of PR #154

Item 79 compares REVIEW against this review. It graded both defects critical.
The text below is item 78's Problem section, copied verbatim on 2026-10-12.
Item 78 was filed from this review, so its Problem is the review's own record
of the two findings.

`fixture.toml` declares the same two defects as `dirty-restore` and
`truncating-write`. This file holds the grading those declarations came from.
Line numbers below are the review's own, read at `head_sha` 78a25a2.

---

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
